#!/usr/bin/env bash
# Git ベースのロールバック
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck disable=SC1091
source "$SCRIPT_DIR/../lib/common.sh"

SESSION_ID="${1:-}"
ENV_NAME="${2:-production}"
CONFIRM="${3:-}"

if [[ -z "$SESSION_ID" || "$CONFIRM" != "--confirm" ]]; then
  log_error "使用方法: rollback_git.sh <session_id> [staging|production] --confirm"
  exit 1
fi

load_env

if [[ "$ENV_NAME" == "staging" ]]; then
  TARGET_BRANCH="${GIT_STAGING_BRANCH:-staging}"
  SSH_HOST="${WP_STAGING_SSH:-}"
  WP_PATH="${WP_STAGING_PATH:-}"
else
  TARGET_BRANCH="${GIT_PRODUCTION_BRANCH:-main}"
  SSH_HOST="${WP_PROD_SSH:-}"
  WP_PATH="${WP_PROD_PATH:-}"
fi

MERGE_COMMIT=$(git log --oneline --grep="merge(wpai): $SESSION_ID" -1 --format="%H" 2>/dev/null || true)

if [[ -z "$MERGE_COMMIT" ]]; then
  log_error "マージコミットが見つかりません: $SESSION_ID"
  exit 1
fi

log_info "ロールバック: revert $MERGE_COMMIT on $TARGET_BRANCH"

git checkout "$TARGET_BRANCH"
git pull origin "$TARGET_BRANCH"
git revert "$MERGE_COMMIT" --no-edit -m 1
git push origin "$TARGET_BRANCH"

if [[ -n "$SSH_HOST" && -n "$WP_PATH" ]]; then
  ssh "$SSH_HOST" "cd '$WP_PATH' && git pull origin '$TARGET_BRANCH' && wp cache flush 2>/dev/null || true"
fi

RECORD_FILE="$ROOT_DIR/deployments/history.jsonl"
echo "{\"action\":\"git_rollback\",\"session_id\":\"$SESSION_ID\",\"env\":\"$ENV_NAME\",\"reverted\":\"$MERGE_COMMIT\",\"timestamp\":\"$(date -u +%Y-%m-%dT%H:%M:%SZ)\"}" >> "$RECORD_FILE"

log_info "Gitロールバック完了"
