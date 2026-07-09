#!/usr/bin/env bash
# WPAIPublisher 共通シェル関数
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "$SCRIPT_DIR/../.." && pwd)"

log_info()  { echo "[INFO]  $(date '+%Y-%m-%d %H:%M:%S') $*"; }
log_warn()  { echo "[WARN]  $(date '+%Y-%m-%d %H:%M:%S') $*" >&2; }
log_error() { echo "[ERROR] $(date '+%Y-%m-%d %H:%M:%S') $*" >&2; }

require_command() {
  if ! command -v "$1" &>/dev/null; then
    log_error "必須コマンドが見つかりません: $1"
    exit 1
  fi
}

load_env() {
  if [[ -f "$ROOT_DIR/config/.env" ]]; then
    set -a
    # shellcheck disable=SC1091
    source <(grep -v '^\s*#' "$ROOT_DIR/config/.env" | grep -v '^\s*$' | sed 's/^/export /')
    set +a
  fi
}

get_session_dir() {
  local session_id="$1"
  echo "$ROOT_DIR/output/$session_id"
}

check_session_ready() {
  local session_id="$1"
  local session_dir
  session_dir="$(get_session_dir "$session_id")"

  if [[ ! -d "$session_dir" ]]; then
    log_error "セッションが見つかりません: $session_id"
    exit 1
  fi
  if [[ ! -f "$session_dir/validation.json" ]]; then
    log_error "検証が未実行です。先に run_validation.py を実行してください"
    exit 1
  fi
  if ! python3 -c "import json; d=json.load(open('$session_dir/validation.json')); exit(0 if d['valid'] else 1)" 2>/dev/null; then
    log_error "検証が失敗しています: $session_id"
    exit 1
  fi
}

create_deploy_snapshot() {
  local session_id="$1"
  local env_name="$2"
  local snapshot_dir="$ROOT_DIR/deployments/$session_id-$env_name-$(date +%Y%m%d%H%M%S)"
  mkdir -p "$snapshot_dir"
  cp -r "$(get_session_dir "$session_id")/wordpress/"* "$snapshot_dir/"
  echo "$snapshot_dir"
}

record_deployment() {
  local session_id="$1"
  local env_name="$2"
  local snapshot_dir="$3"
  local record_file="$ROOT_DIR/deployments/history.jsonl"
  local timestamp
  timestamp="$(date -u +%Y-%m-%dT%H:%M:%SZ)"
  echo "{\"session_id\":\"$session_id\",\"env\":\"$env_name\",\"snapshot\":\"$snapshot_dir\",\"timestamp\":\"$timestamp\"}" >> "$record_file"
}
