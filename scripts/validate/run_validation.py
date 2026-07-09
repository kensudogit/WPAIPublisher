#!/usr/bin/env python3
"""変換後ファイルの検証"""

import argparse
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))

from lib.config import get_output_dir, load_config  # noqa: E402


def check_php_syntax(php_files: list[Path]) -> list[str]:
    errors = []
    for f in php_files:
        try:
            result = subprocess.run(
                ["php", "-l", str(f)],
                capture_output=True,
                text=True,
                timeout=10,
            )
            if result.returncode != 0:
                errors.append(f"PHP構文エラー: {f.name} - {result.stderr.strip()}")
        except FileNotFoundError:
            errors.append("php コマンドが見つかりません（PHP構文チェックをスキップ）")
            break
    return errors


def check_required_files(wp_dir: Path, target_type: str) -> list[str]:
    errors = []
    if target_type == "block":
        if not list(wp_dir.glob("block.json")) and not list(wp_dir.glob("**/block.json")):
            errors.append("block.json が見つかりません")
        if not list(wp_dir.glob("*.php")) and not list(wp_dir.glob("**/*.php")):
            errors.append("PHPテンプレートファイルが見つかりません")
    elif target_type == "theme":
        if not (wp_dir / "style.css").exists():
            errors.append("style.css（テーマヘッダー）が見つかりません")
        if not (wp_dir / "index.php").exists():
            errors.append("index.php が見つかりません")
    elif target_type == "page":
        if not list(wp_dir.glob("*.html")) and not list(wp_dir.glob("*.php")):
            errors.append("ページコンテンツファイルが見つかりません")
    return errors


def check_security(wp_dir: Path) -> list[str]:
    warnings = []
    dangerous_patterns = ["eval(", "exec(", "system(", "shell_exec(", "passthru("]
    for f in wp_dir.rglob("*"):
        if f.is_file() and f.suffix in (".php", ".js"):
            content = f.read_text(encoding="utf-8", errors="ignore")
            for pattern in dangerous_patterns:
                if pattern in content:
                    warnings.append(f"危険な関数の使用: {f.relative_to(wp_dir)} に {pattern}")
    return warnings


def main() -> int:
    parser = argparse.ArgumentParser(description="変換後ファイルの検証")
    parser.add_argument("session_id", help="セッションID")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    session_dir = get_output_dir() / args.session_id
    task_path = session_dir / "task.json"
    wp_dir = session_dir / "wordpress"

    if not task_path.exists():
        print(f"ERROR: セッションが見つかりません: {session_dir}", file=sys.stderr)
        return 1
    if not wp_dir.exists():
        print(f"ERROR: wordpress/ が見つかりません: {wp_dir}", file=sys.stderr)
        return 1

    with open(task_path, encoding="utf-8") as f:
        task = json.load(f)

    target_type = task["manifest"]["target"]["type"]
    errors: list[str] = []
    warnings: list[str] = []

    errors.extend(check_required_files(wp_dir, target_type))

    php_files = list(wp_dir.rglob("*.php"))
    if php_files:
        try:
            config = load_config()
            if config.get("validation", {}).get("php_lint", True):
                errors.extend(check_php_syntax(php_files))
        except FileNotFoundError:
            errors.extend(check_php_syntax(php_files))

    warnings.extend(check_security(wp_dir))

    result = {
        "session_id": args.session_id,
        "valid": len(errors) == 0,
        "errors": errors,
        "warnings": warnings,
    }

    # 検証結果を保存
    result_path = session_dir / "validation.json"
    with open(result_path, "w", encoding="utf-8") as f:
        json.dump(result, f, indent=2, ensure_ascii=False)

    # 検証ステータスを task に反映して DB 同期
    try:
        with open(task_path, encoding="utf-8") as f:
            task_data = json.load(f)
        task_data["status"] = "validated" if not errors else "validation_failed"
        task_data["validated_at"] = __import__("datetime").datetime.now(
            __import__("datetime").timezone.utc
        ).isoformat()
        with open(task_path, "w", encoding="utf-8") as f:
            json.dump(task_data, f, indent=2, ensure_ascii=False)
        from lib.sync_hook import sync_session  # noqa: E402

        sync_session(args.session_id)
    except Exception:  # noqa: BLE001
        pass

    if args.json:
        print(json.dumps(result, indent=2, ensure_ascii=False))
    else:
        if errors:
            print(f"VALIDATION FAILED: {args.session_id}")
            for e in errors:
                print(f"  ERROR: {e}")
        else:
            print(f"VALIDATION OK: {args.session_id}")
        for w in warnings:
            print(f"  WARNING: {w}")

    if not errors:
        print(f"\n次のステップ: bash scripts/deploy/deploy_staging.sh {args.session_id}")

    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
