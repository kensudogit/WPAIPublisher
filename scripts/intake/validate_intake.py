#!/usr/bin/env python3
"""受け取ったAI出力（intake）のバリデーション"""

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))

from lib.config import get_intake_dir  # noqa: E402


def validate_manifest(manifest: dict, intake_dir: Path) -> list[str]:
    errors: list[str] = []

    if manifest.get("version") != "1.0":
        errors.append(f"未対応のマニフェストバージョン: {manifest.get('version')}")

    source = manifest.get("source", {})
    if not source.get("tool"):
        errors.append("source.tool が未設定です")
    if not source.get("generated_at"):
        errors.append("source.generated_at が未設定です")
    else:
        try:
            datetime.fromisoformat(source["generated_at"].replace("Z", "+00:00"))
        except ValueError:
            errors.append(f"source.generated_at の形式が不正: {source['generated_at']}")

    target = manifest.get("target", {})
    if not target.get("type"):
        errors.append("target.type が未設定です")
    valid_types = {"theme", "block", "page", "template-part", "custom-css"}
    if target.get("type") and target["type"] not in valid_types:
        errors.append(f"target.type が不正: {target['type']} (有効: {valid_types})")

    files = manifest.get("files", [])
    if not files:
        errors.append("files が空です")

    for f in files:
        fpath = intake_dir / f.get("path", "")
        if not fpath.exists():
            errors.append(f"ファイルが見つかりません: {f.get('path')}")
        if not f.get("role"):
            errors.append(f"role が未設定: {f.get('path')}")

    return errors


def main() -> int:
    parser = argparse.ArgumentParser(description="AI出力 intake のバリデーション")
    parser.add_argument(
        "intake_path",
        nargs="?",
        default=None,
        help="intake ディレクトリ（manifest.json を含む）",
    )
    parser.add_argument("--json", action="store_true", help="JSON形式で結果を出力")
    args = parser.parse_args()

    if args.intake_path:
        intake_dir = Path(args.intake_path)
    else:
        incoming = get_intake_dir() / "incoming"
        candidates = sorted(
            [d for d in incoming.iterdir() if d.is_dir()],
            key=lambda p: p.stat().st_mtime,
            reverse=True,
        )
        if not candidates:
            print("ERROR: intake/incoming/ にパッケージがありません", file=sys.stderr)
            return 1
        intake_dir = candidates[0]

    manifest_path = intake_dir / "manifest.json"
    if not manifest_path.exists():
        print(f"ERROR: manifest.json が見つかりません: {intake_dir}", file=sys.stderr)
        return 1

    with open(manifest_path, encoding="utf-8") as f:
        manifest = json.load(f)

    errors = validate_manifest(manifest, intake_dir)

    if args.json:
        print(json.dumps({"valid": len(errors) == 0, "errors": errors, "path": str(intake_dir)}))
    else:
        if errors:
            print(f"VALIDATION FAILED: {intake_dir}")
            for e in errors:
                print(f"  - {e}")
        else:
            print(f"VALIDATION OK: {intake_dir}")
            print(f"  target: {manifest['target']['type']}")
            print(f"  files: {len(manifest['files'])}")

    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
