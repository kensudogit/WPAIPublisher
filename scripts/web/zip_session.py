#!/usr/bin/env python3
"""セッション関連ファイルを ZIP にまとめる（Web ダウンロード用）"""

from __future__ import annotations

import argparse
import json
import re
import sys
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

SESSION_RE = re.compile(r"^[a-zA-Z0-9._-]+$")


def collect_roots(session_id: str) -> list[tuple[str, Path]]:
    """ZIP 内プレフィックスとソースディレクトリの組を返す。"""
    roots: list[tuple[str, Path]] = []
    session_dir = ROOT / "output" / session_id
    if session_dir.is_dir():
        roots.append((f"output/{session_id}", session_dir))

    incoming = ROOT / "intake" / "incoming"
    if incoming.is_dir():
        for pkg in sorted(incoming.iterdir()):
            if not pkg.is_dir():
                continue
            # パッケージ名に session_id が含まれる、または task/manifest で紐づく
            if session_id in pkg.name:
                roots.append((f"incoming/{pkg.name}", pkg))
                continue
            task = pkg / "task.json"
            if task.is_file():
                try:
                    data = json.loads(task.read_text(encoding="utf-8"))
                    if str(data.get("session_id") or "") == session_id:
                        roots.append((f"incoming/{pkg.name}", pkg))
                except (OSError, json.JSONDecodeError):
                    pass

    # 重複除去（同じ Path）
    seen: set[Path] = set()
    unique: list[tuple[str, Path]] = []
    for prefix, path in roots:
        resolved = path.resolve()
        if resolved in seen:
            continue
        seen.add(resolved)
        unique.append((prefix, path))
    return unique


def add_tree(zf: zipfile.ZipFile, prefix: str, root: Path) -> int:
    count = 0
    root = root.resolve()
    for path in root.rglob("*"):
        if not path.is_file():
            continue
        # 一時ファイル・隠し巨大キャッシュは除外
        if path.name.startswith(".") and path.suffix in {".tmp", ".lock"}:
            continue
        try:
            rel = path.resolve().relative_to(root)
        except ValueError:
            continue
        arc = f"{prefix}/{rel.as_posix()}"
        zf.write(path, arcname=arc)
        count += 1
    return count


def main() -> int:
    parser = argparse.ArgumentParser(description="ZIP session files for download")
    parser.add_argument("session_id")
    parser.add_argument("zip_path", help="出力 ZIP パス")
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--list-only", action="store_true", help="ZIP せず一覧のみ")
    args = parser.parse_args()

    session_id = args.session_id.strip()
    if not SESSION_RE.match(session_id):
        print(json.dumps({"ok": False, "error": "invalid session id"}, ensure_ascii=False))
        return 1

    roots = collect_roots(session_id)
    if not roots:
        payload = {
            "ok": False,
            "error": f"セッション関連ファイルが見つかりません: {session_id}",
            "session_id": session_id,
        }
        print(json.dumps(payload, ensure_ascii=False))
        return 1

    if args.list_only:
        files: list[dict] = []
        for prefix, root in roots:
            for path in root.rglob("*"):
                if path.is_file():
                    rel = path.relative_to(root).as_posix()
                    files.append(
                        {
                            "path": f"{prefix}/{rel}",
                            "size": path.stat().st_size,
                        }
                    )
        print(
            json.dumps(
                {"ok": True, "session_id": session_id, "roots": [p for p, _ in roots], "files": files},
                ensure_ascii=False,
            )
        )
        return 0

    zip_path = Path(args.zip_path)
    zip_path.parent.mkdir(parents=True, exist_ok=True)
    total = 0
    with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        for prefix, root in roots:
            total += add_tree(zf, prefix, root)

    if total == 0:
        zip_path.unlink(missing_ok=True)
        print(
            json.dumps(
                {"ok": False, "error": "ZIP に含めるファイルがありません", "session_id": session_id},
                ensure_ascii=False,
            )
        )
        return 1

    if args.json:
        print(
            json.dumps(
                {
                    "ok": True,
                    "session_id": session_id,
                    "zip_path": str(zip_path),
                    "file_count": total,
                    "roots": [p for p, _ in roots],
                    "size": zip_path.stat().st_size,
                },
                ensure_ascii=False,
            )
        )
    return 0


if __name__ == "__main__":
    sys.exit(main())
