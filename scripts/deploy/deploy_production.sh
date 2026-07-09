#!/usr/bin/env bash
# 本番環境へのデプロイ（ステージング確認後）
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck disable=SC1091
source "$SCRIPT_DIR/../lib/common.sh"

SESSION_ID="${1:-}"
CONFIRM="${2:-}"

if [[ -z "$SESSION_ID" ]]; then
  log_error "使用方法: deploy_production.sh <session_id> [--confirm]"
  exit 1
fi

if [[ "$CONFIRM" != "--confirm" ]]; then
  log_error "本番デプロイには確認フラグが必要です:"
  log_error "  bash scripts/deploy/deploy_production.sh $SESSION_ID --confirm"
  exit 1
fi

load_env
check_session_ready "$SESSION_ID"

SESSION_DIR="$(get_session_dir "$SESSION_ID")"

# ステージングデプロイ済みか確認
STATUS=$(python3 -c "import json; print(json.load(open('$SESSION_DIR/task.json')).get('status',''))")
if [[ "$STATUS" != "deployed_staging" ]]; then
  log_error "ステージングデプロイが未完了です（status: $STATUS）"
  log_error "先に deploy_staging.sh を実行し、ステージングで確認してください"
  exit 1
fi

WP_DIR="$SESSION_DIR/wordpress"
SNAPSHOT_DIR="$(create_deploy_snapshot "$SESSION_ID" "production")"

log_info "本番デプロイ開始: $SESSION_ID"
log_info "スナップショット: $SNAPSHOT_DIR"

TARGET_TYPE=$(python3 -c "import json; print(json.load(open('$SESSION_DIR/task.json'))['manifest']['target']['type'])")

case "$TARGET_TYPE" in
  block|theme|template-part)
    if [[ -n "${WP_PROD_SSH:-}" && -n "${WP_PROD_PATH:-}" ]]; then
      THEME_PATH="${WP_PROD_PATH}/wp-content/themes"
      THEME_SLUG=$(python3 -c "import json; print(json.load(open('$SESSION_DIR/task.json'))['manifest']['target'].get('theme_slug','custom-theme'))")

      if [[ "$TARGET_TYPE" == "block" ]]; then
        BLOCK_NAME=$(python3 -c "import json; print(json.load(open('$SESSION_DIR/task.json'))['manifest']['target'].get('block_name',''))")
        REMOTE_DIR="$THEME_PATH/$THEME_SLUG/blocks/$BLOCK_NAME"
      else
        REMOTE_DIR="$THEME_PATH/$THEME_SLUG"
      fi

      # 本番デプロイ前にバックアップ
      BACKUP_DIR="$ROOT_DIR/deployments/backup-prod-$(date +%Y%m%d%H%M%S)"
      mkdir -p "$BACKUP_DIR"
      log_info "本番バックアップ取得: $BACKUP_DIR"
      scp -r "$WP_PROD_SSH:$REMOTE_DIR/" "$BACKUP_DIR/" 2>/dev/null || log_warn "バックアップ対象が存在しません（新規デプロイ）"

      log_info "リモート同期: $WP_PROD_SSH:$REMOTE_DIR"
      ssh "$WP_PROD_SSH" "mkdir -p '$REMOTE_DIR'"
      scp -r "$WP_DIR/"* "$WP_PROD_SSH:$REMOTE_DIR/"

      ssh "$WP_PROD_SSH" "cd '$WP_PROD_PATH' && wp cache flush 2>/dev/null || true"
    else
      log_error "WP_PROD_SSH / WP_PROD_PATH が未設定です"
      exit 1
    fi
    ;;

  page)
    log_info "REST API によるページ公開（本番）"
    python3 "$ROOT_DIR/scripts/deploy/push_page.py" \
      --env production \
      --session "$SESSION_ID" \
      --status publish
    ;;

  custom-css)
    python3 "$ROOT_DIR/scripts/deploy/push_custom_css.py" \
      --env production \
      --session "$SESSION_ID"
    ;;

  *)
    log_error "未対応のターゲット種別: $TARGET_TYPE"
    exit 1
    ;;
esac

record_deployment "$SESSION_ID" "production" "$SNAPSHOT_DIR"

python3 -c "
import json
from pathlib import Path
task_path = Path('$SESSION_DIR/task.json')
task = json.loads(task_path.read_text())
task['status'] = 'deployed_production'
task['production_url'] = '${WP_PROD_URL:-}'
task_path.write_text(json.dumps(task, indent=2, ensure_ascii=False))
"

log_info "本番デプロイ完了"
log_info "確認URL: ${WP_PROD_URL:-（未設定）}"
