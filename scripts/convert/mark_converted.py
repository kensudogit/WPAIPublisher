#!/usr/bin/env python3
"""Claude Code による変換完了をマークする"""

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))

from lib.config import get_output_dir  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description="変換完了のマーク")
    parser.add_argument("session_id", help="セッションID")
    parser.add_argument("--notes", default="", help="変換メモ")
    args = parser.parse_args()

    session_dir = get_output_dir() / args.session_id
    task_path = session_dir / "task.json"

    if not task_path.exists():
        print(f"ERROR: セッションが見つかりません: {session_dir}", file=sys.stderr)
        return 1

    wp_dir = session_dir / "wordpress"
    if not wp_dir.exists() or not any(wp_dir.iterdir()):
        print(f"ERROR: wordpress/ ディレクトリが空です: {wp_dir}", file=sys.stderr)
        return 1

    with open(task_path, encoding="utf-8") as f:
        task = json.load(f)

    task["status"] = "converted"
    task["converted_at"] = datetime.now(timezone.utc).isoformat()
    task["notes"] = args.notes

    with open(task_path, "w", encoding="utf-8") as f:
        json.dump(task, f, indent=2, ensure_ascii=False)

    from lib.sync_hook import sync_session  # noqa: E402

    sync_session(args.session_id)

    print(f"変換完了: {args.session_id}")
    print("次のステップ: python scripts/validate/run_validation.py " + args.session_id)
    return 0


if __name__ == "__main__":
    sys.exit(main())
