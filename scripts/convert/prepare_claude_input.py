#!/usr/bin/env python3
"""Claude Code への変換入力を準備する"""

import argparse
import json
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))

from lib.config import get_intake_dir, get_output_dir  # noqa: E402


def prepare_claude_input(intake_dir: Path, output_session: Path) -> dict:
    manifest_path = intake_dir / "manifest.json"
    with open(manifest_path, encoding="utf-8") as f:
        manifest = json.load(f)

    output_session.mkdir(parents=True, exist_ok=True)

    # ソースファイルをコピー
    source_dir = output_session / "source"
    source_dir.mkdir(exist_ok=True)
    for file_entry in manifest["files"]:
        src = intake_dir / file_entry["path"]
        dst = source_dir / Path(file_entry["path"]).name
        shutil.copy2(src, dst)

    # 変換タスク情報
    task = {
        "session_id": output_session.name,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "manifest": manifest,
        "source_dir": str(source_dir),
        "target_dir": str(output_session / "wordpress"),
        "prompt_file": str(ROOT / "prompts" / "convert-to-wp.md"),
        "status": "pending_conversion",
    }

    task_path = output_session / "task.json"
    with open(task_path, "w", encoding="utf-8") as f:
        json.dump(task, f, indent=2, ensure_ascii=False)

    # Claude Code 用の実行指示
    instructions = f"""# Claude Code 変換タスク

## セッションID
{output_session.name}

## 手順
1. `prompts/convert-to-wp.md` のプロンプトを読み込む
2. `output/{output_session.name}/source/` のファイルを WordPress 向けに変換
3. 変換結果を `output/{output_session.name}/wordpress/` に出力
4. `prompts/validate-theme.md` に従い自己検証
5. 完了後、以下を実行:
   ```
   python scripts/convert/mark_converted.py {output_session.name}
   ```

## マニフェスト
```json
{json.dumps(manifest, indent=2, ensure_ascii=False)}
```
"""
    (output_session / "CLAUDE_INSTRUCTIONS.md").write_text(instructions, encoding="utf-8")

    return task


def main() -> int:
    parser = argparse.ArgumentParser(description="Claude Code 変換入力の準備")
    parser.add_argument("intake_path", nargs="?", help="intake ディレクトリ")
    parser.add_argument("--session-id", help="セッションID（省略時は自動生成）")
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

    session_id = args.session_id or datetime.now().strftime("%Y%m%d-%H%M%S")
    output_session = get_output_dir() / session_id

    if output_session.exists():
        print(f"ERROR: セッションが既に存在します: {output_session}", file=sys.stderr)
        return 1

    task = prepare_claude_input(intake_dir, output_session)

    from lib.sync_hook import sync_session  # noqa: E402

    sync_session(session_id)

    print(f"セッション作成: {output_session}")
    print(f"Claude Code 指示: {output_session / 'CLAUDE_INSTRUCTIONS.md'}")
    print(f"プロンプト: {task['prompt_file']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
