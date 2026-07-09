#!/usr/bin/env bash
# ロールバック実行
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck disable=SC1091
source "$SCRIPT_DIR/../lib/common.sh"

SESSION_ID="${1:-}"
ENV_NAME="${2:-production}"
CONFIRM="${3:-}"

if [[ -z "$SESSION_ID" ]]; then
  log_error "使用方法: rollback.sh <session_id> [staging|production] [--confirm]"
  exit 1
fi

if [[ "$CONFIRM" != "--confirm" ]]; then
  log_error "ロールバックには確認フラグが必要です:"
  log_error "  bash scripts/rollback/rollback.sh $SESSION_ID $ENV_NAME --confirm"
  exit 1
fi

load_env

# バックアップを検索
BACKUP_PATTERN="$ROOT_DIR/deployments/backup-${ENV_NAME%-*}-*"
LATEST_BACKUP=""
if [[ "$ENV_NAME" == "production" ]]; then
  LATEST_BACKUP=$(ls -dt "$ROOT_DIR"/deployments/backup-prod-* 2>/dev/null | head -1 || true)
fi

if [[ -z "$LATEST_BACKUP" ]]; then
  # デプロイ履歴から直前のスナップショットを探す
  HISTORY="$ROOT_DIR/deployments/history.jsonl"
  if [[ -f "$HISTORY" ]]; then
    LATEST_BACKUP=$(python3 -c "
import json, sys
entries = [json.loads(l) for l in open('$HISTORY') if l.strip()]
prev = [e for e in entries if e['session_id'] != '$SESSION_ID' and e['env'] == '$ENV_NAME']
if prev:
    print(prev[-1]['snapshot'])
" 2>/dev/null || true)
  fi
fi

if [[ -z "$LATEST_BACKUP" || ! -d "$LATEST_BACKUP" ]]; then
  log_error "ロールバック用バックアップが見つかりません"
  log_error "docs/ROLLBACK.md の手動手順を参照してください"
  exit 1
fi

log_info "ロールバック開始"
log_info "  セッション: $SESSION_ID"
log_info "  環境: $ENV_NAME"
log_info "  復元元: $LATEST_BACKUP"

if [[ "$ENV_NAME" == "production" && -n "${WP_PROD_SSH:-}" && -n "${WP_PROD_PATH:-}" ]]; then
  SESSION_DIR="$(get_session_dir "$SESSION_ID")"
  THEME_SLUG=$(python3 -c "import json; print(json.load(open('$SESSION_DIR/task.json'))['manifest']['target'].get('theme_slug','custom-theme'))" 2>/dev/null || echo "custom-theme")
  TARGET_TYPE=$(python3 -c "import json; print(json.load(open('$SESSION_DIR/task.json'))['manifest']['target']['type'])" 2>/dev/null || echo "block")

  if [[ "$TARGET_TYPE" == "block" ]]; then
    BLOCK_NAME=$(python3 -c "import json; print(json.load(open('$SESSION_DIR/task.json'))['manifest']['target'].get('block_name',''))")
    REMOTE_DIR="${WP_PROD_PATH}/wp-content/themes/${THEME_SLUG}/blocks/${BLOCK_NAME}"
  else
    REMOTE_DIR="${WP_PROD_PATH}/wp-content/themes/${THEME_SLUG}"
  fi

  log_info "リモート復元: $WP_PROD_SSH:$REMOTE_DIR"
  scp -r "$LATEST_BACKUP/"* "$WP_PROD_SSH:$REMOTE_DIR/"
  ssh "$WP_PROD_SSH" "cd '$WP_PROD_PATH' && wp cache flush 2>/dev/null || true"
elif [[ "$ENV_NAME" == "staging" && -n "${WP_STAGING_SSH:-}" && -n "${WP_STAGING_PATH:-}" ]]; then
  SESSION_DIR="$(get_session_dir "$SESSION_ID")"
  THEME_SLUG=$(python3 -c "import json; print(json.load(open('$SESSION_DIR/task.json'))['manifest']['target'].get('theme_slug','custom-theme'))" 2>/dev/null || echo "custom-theme")
  TARGET_TYPE=$(python3 -c "import json; print(json.load(open('$SESSION_DIR/task.json'))['manifest']['target']['type'])" 2>/dev/null || echo "block")

  if [[ "$TARGET_TYPE" == "block" ]]; then
    BLOCK_NAME=$(python3 -c "import json; print(json.load(open('$SESSION_DIR/task.json'))['manifest']['target'].get('block_name',''))")
    REMOTE_DIR="${WP_STAGING_PATH}/wp-content/themes/${THEME_SLUG}/blocks/${BLOCK_NAME}"
  else
    REMOTE_DIR="${WP_STAGING_PATH}/wp-content/themes/${THEME_SLUG}"
  fi

  scp -r "$LATEST_BACKUP/"* "$WP_STAGING_SSH:$REMOTE_DIR/"
  ssh "$WP_STAGING_SSH" "cd '$WP_STAGING_PATH' && wp cache flush 2>/dev/null || true"
else
  log_warn "SSH設定が未完了。バックアップファイルの場所:"
  log_warn "  $LATEST_BACKUP"
  log_warn "手動でサーバーへ復元してください"
fi

# ロールバック記録
RECORD_FILE="$ROOT_DIR/deployments/history.jsonl"
echo "{\"action\":\"rollback\",\"session_id\":\"$SESSION_ID\",\"env\":\"$ENV_NAME\",\"restored_from\":\"$LATEST_BACKUP\",\"timestamp\":\"$(date -u +%Y-%m-%dT%H:%M:%SZ)\"}" >> "$RECORD_FILE"

log_info "ロールバック完了"
