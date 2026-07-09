#!/usr/bin/env python3
"""ローカル output/ のセッションを PostgreSQL へ同期"""

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))

from lib.session_store import database_url, ensure_schema, list_sessions, sync_all_sessions, upsert_from_task_file  # noqa: E402
from lib.config import get_output_dir  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description="セッションを PostgreSQL へ同期")
    parser.add_argument("action", choices=["sync", "list", "push"])
    parser.add_argument("session_id", nargs="?", help="push 時のセッションID")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    if not database_url():
        print("ERROR: DATABASE_URL が未設定です（config/.env または環境変数）", file=sys.stderr)
        return 1

    if args.action == "sync":
        ensure_schema()
        synced = sync_all_sessions(get_output_dir())
        print(f"Synced {len(synced)} session(s) to PostgreSQL")
        for s in synced:
            print(f"  - {s}")
        return 0

    if args.action == "push":
        if not args.session_id:
            print("ERROR: session_id が必要です", file=sys.stderr)
            return 1
        session_dir = get_output_dir() / args.session_id
        if not upsert_from_task_file(session_dir):
            print(f"ERROR: 同期失敗: {args.session_id}", file=sys.stderr)
            return 1
        print(f"Pushed: {args.session_id}")
        return 0

    rows = list_sessions()
    if args.json:
        import json
        print(json.dumps(rows, indent=2, ensure_ascii=False))
    else:
        print(f"{'ID':<24} {'Status':<22} {'Target':<12} {'Updated'}")
        print("-" * 72)
        for r in rows:
            print(f"{r['id']:<24} {r['status']:<22} {r['target']:<12} {r.get('updated_at') or '-'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
