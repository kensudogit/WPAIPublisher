#!/usr/bin/env bash
# Git ベースのステージング/本番デプロイ
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck disable=SC1091
source "$SCRIPT_DIR/../lib/common.sh"

ENV_NAME="${1:-staging}"
SESSION_ID="${2:-}"
CONFIRM="${3:-}"

if [[ -z "$SESSION_ID" ]]; then
  log_error "使用方法: deploy_via_git.sh <staging|production> <session_id> [--confirm]"
  exit 1
fi

if [[ "$ENV_NAME" == "production" && "$CONFIRM" != "--confirm" ]]; then
  log_error "本番デプロイには --confirm が必要です"
  exit 1
fi

load_env
check_session_ready "$SESSION_ID"

SESSION_DIR="$(get_session_dir "$SESSION_ID")"
BRANCH="wpai/${SESSION_ID}"

if [[ "$ENV_NAME" == "staging" ]]; then
  TARGET_BRANCH="${GIT_STAGING_BRANCH:-staging}"
else
  TARGET_BRANCH="${GIT_PRODUCTION_BRANCH:-main}"
fi

log_info "Gitデプロイ: $SESSION_ID → $TARGET_BRANCH"

# マージ
git fetch origin
git checkout "$TARGET_BRANCH"
git pull origin "$TARGET_BRANCH"

if git show-ref --verify --quiet "refs/heads/$BRANCH" || git ls-remote --heads origin "$BRANCH" | grep -q "$BRANCH"; then
  git merge "origin/$BRANCH" --no-edit -m "merge(wpai): $SESSION_ID into $TARGET_BRANCH"
else
  log_error "ブランチが見つかりません: $BRANCH"
  log_error "先に scripts/git/create_pr.py を実行してください"
  exit 1
fi

git push origin "$TARGET_BRANCH"

# リモートサーバーへpull（SSH設定がある場合）
if [[ "$ENV_NAME" == "staging" && -n "${WP_STAGING_SSH:-}" && -n "${WP_STAGING_PATH:-}" ]]; then
  ssh "$WP_STAGING_SSH" "cd '$WP_STAGING_PATH' && git pull origin '$TARGET_BRANCH' && wp cache flush 2>/dev/null || true"
elif [[ "$ENV_NAME" == "production" && -n "${WP_PROD_SSH:-}" && -n "${WP_PROD_PATH:-}" ]]; then
  ssh "$WP_PROD_SSH" "cd '$WP_PROD_PATH' && git pull origin '$TARGET_BRANCH' && wp cache flush 2>/dev/null || true"
fi

record_deployment "$SESSION_ID" "$ENV_NAME" "$SESSION_DIR/wordpress"

log_info "Gitデプロイ完了: $TARGET_BRANCH"
