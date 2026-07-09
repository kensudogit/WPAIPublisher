#!/usr/bin/env python3
"""選択した HTML から intake → validate → convert prepare まで実行"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts" / "intake"))

from select_files import create_package  # noqa: E402


def run(cmd: list[str], *, quiet: bool = False) -> int:
    if not quiet:
        print("+", " ".join(cmd))
        return subprocess.run(cmd, cwd=str(ROOT)).returncode
    result = subprocess.run(
        cmd,
        cwd=str(ROOT),
        stdout=subprocess.DEVNULL,
        stderr=subprocess.PIPE,
        text=True,
    )
    if result.returncode != 0 and result.stderr:
        print(result.stderr, file=sys.stderr)
    return result.returncode


def main() -> int:
    parser = argparse.ArgumentParser(description="選択HTMLをパイプライン投入")
    parser.add_argument("source_dir", help="HTML が含まれるフォルダ")
    parser.add_argument("--select", action="append", required=True, help="HTML 相対パス（複数可）")
    parser.add_argument("--package-name")
    parser.add_argument("--session-id")
    parser.add_argument("--target-type", default="page", choices=["page", "block", "theme", "template-part", "custom-css"])
    parser.add_argument("--theme-slug", default="custom-theme")
    parser.add_argument("--tool", default="other")
    parser.add_argument("--notes", default="")
    parser.add_argument("--agent", action="store_true", help="convert prepare 後に agent run")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()
    quiet = args.json

    dest = create_package(
        Path(args.source_dir),
        args.select,
        package_name=args.package_name,
        target_type=args.target_type,
        theme_slug=args.theme_slug,
        tool=args.tool,
        notes=args.notes,
    )

    if run([sys.executable, str(ROOT / "wpaipublish.py"), "intake", "validate", str(dest)], quiet=quiet) != 0:
        return 1

    session_id = args.session_id or datetime.now().strftime("%Y%m%d-%H%M%S")
    prepare_cmd = [
        sys.executable,
        str(ROOT / "wpaipublish.py"),
        "convert",
        "prepare",
        str(dest),
        "--session-id",
        session_id,
    ]
    if run(prepare_cmd, quiet=quiet) != 0:
        return 1

    if args.agent:
        if run([sys.executable, str(ROOT / "wpaipublish.py"), "agent", "run", session_id], quiet=quiet) != 0:
            return 1

    result = {
        "package": str(dest),
        "session_id": session_id,
        "selected": args.select,
        "next": [
            f"python wpaipublish.py ai route --stage wp_conversion --session {session_id}",
            f"python wpaipublish.py convert mark-done {session_id}",
            f"python wpaipublish.py quality run {session_id}",
            f"python wpaipublish.py deploy staging {session_id}",
        ],
    }
    if args.json:
        print(json.dumps(result, indent=2, ensure_ascii=False))
    else:
        print("\nPipeline prepared")
        print(f"  package: {dest}")
        print(f"  session: {session_id}")
        print("  next:")
        for step in result["next"]:
            print(f"    {step}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
