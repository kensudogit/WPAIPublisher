#!/usr/bin/env bash
# ステージング環境へのデプロイ
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck disable=SC1091
source "$SCRIPT_DIR/../lib/common.sh"

SESSION_ID="${1:-}"
if [[ -z "$SESSION_ID" ]]; then
  log_error "使用方法: deploy_staging.sh <session_id>"
  exit 1
fi

load_env
check_session_ready "$SESSION_ID"

SESSION_DIR="$(get_session_dir "$SESSION_ID")"
WP_DIR="$SESSION_DIR/wordpress"
SNAPSHOT_DIR="$(create_deploy_snapshot "$SESSION_ID" "staging")"

log_info "ステージングデプロイ開始: $SESSION_ID"
log_info "スナップショット: $SNAPSHOT_DIR"

# ターゲット種別を取得
TARGET_TYPE=$(python3 -c "import json; print(json.load(open('$SESSION_DIR/task.json'))['manifest']['target']['type'])")

case "$TARGET_TYPE" in
  block|theme|template-part)
    log_info "WP-CLI によるファイルデプロイ（ステージング）"
    if [[ -n "${WP_STAGING_SSH:-}" && -n "${WP_STAGING_PATH:-}" ]]; then
      THEME_PATH="${WP_STAGING_PATH}/wp-content/themes"
      THEME_SLUG=$(python3 -c "import json; print(json.load(open('$SESSION_DIR/task.json'))['manifest']['target'].get('theme_slug','custom-theme'))")

      if [[ "$TARGET_TYPE" == "block" ]]; then
        BLOCK_NAME=$(python3 -c "import json; print(json.load(open('$SESSION_DIR/task.json'))['manifest']['target'].get('block_name',''))")
        REMOTE_DIR="$THEME_PATH/$THEME_SLUG/blocks/$BLOCK_NAME"
      else
        REMOTE_DIR="$THEME_PATH/$THEME_SLUG"
      fi

      log_info "リモート同期: $WP_STAGING_SSH:$REMOTE_DIR"
      ssh "$WP_STAGING_SSH" "mkdir -p '$REMOTE_DIR'"
      scp -r "$WP_DIR/"* "$WP_STAGING_SSH:$REMOTE_DIR/"

      log_info "キャッシュクリア"
      ssh "$WP_STAGING_SSH" "cd '$WP_STAGING_PATH' && wp cache flush 2>/dev/null || true"
    else
      log_warn "WP_STAGING_SSH が未設定。ローカル output/ のみ更新済み"
      log_warn "手動でステージングサーバーへファイルをアップロードしてください"
    fi
    ;;

  page)
    log_info "REST API によるページ更新（ステージング・下書き）"
    python3 "$ROOT_DIR/scripts/deploy/push_page.py" \
      --env staging \
      --session "$SESSION_ID" \
      --status draft
    ;;

  custom-css)
    log_info "カスタムCSSのデプロイ（ステージング）"
    python3 "$ROOT_DIR/scripts/deploy/push_custom_css.py" \
      --env staging \
      --session "$SESSION_ID"
    ;;

  *)
    log_error "未対応のターゲット種別: $TARGET_TYPE"
    exit 1
    ;;
esac

record_deployment "$SESSION_ID" "staging" "$SNAPSHOT_DIR"

# デプロイ状態を更新
python3 -c "
import json
from pathlib import Path
task_path = Path('$SESSION_DIR/task.json')
task = json.loads(task_path.read_text())
task['status'] = 'deployed_staging'
task['staging_url'] = '${WP_STAGING_URL:-}'
task_path.write_text(json.dumps(task, indent=2, ensure_ascii=False))
"

log_info "ステージングデプロイ完了"
log_info "確認URL: ${WP_STAGING_URL:-（未設定）}"
log_info ""
log_info "確認後、本番デプロイ:"
log_info "  bash scripts/deploy/deploy_production.sh $SESSION_ID"
