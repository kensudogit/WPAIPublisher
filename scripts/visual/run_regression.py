#!/usr/bin/env python3
"""Playwright ビジュアル回帰テスト Python ラッパー"""

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def main() -> int:
    parser = argparse.ArgumentParser(description="ビジュアル回帰テスト")
    parser.add_argument("session_id", help="セッションID")
    parser.add_argument("--env", default="staging", choices=["staging", "production"])
    parser.add_argument("--update", action="store_true", help="ベースライン更新")
    parser.add_argument("--url", help="ベースURL（省略時は環境変数）")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    env_prefix = "WP_STAGING" if args.env == "staging" else "WP_PROD"
    base_url = args.url or os.environ.get(f"{env_prefix}_URL", "")

    cmd = ["node", str(ROOT / "scripts" / "visual" / "run_regression.mjs"), args.session_id]
    if args.update:
        cmd.append("--update")
    if base_url:
        cmd.extend(["--url", base_url])

    result = subprocess.run(cmd, cwd=str(ROOT))
    report_path = ROOT / "output" / args.session_id / "visual_regression.json"

    if args.json and report_path.exists():
        print(report_path.read_text(encoding="utf-8"))

    return result.returncode


if __name__ == "__main__":
    sys.exit(main())
