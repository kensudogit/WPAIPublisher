#!/usr/bin/env python3
"""ナレッジベースへのドキュメントインデックス作成"""

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))

from lib.config import get_knowledge_dir, get_session_dir  # noqa: E402
from knowledge.vector_store import VectorStore  # noqa: E402

INDEXABLE_EXTENSIONS = {".md", ".php", ".css", ".js", ".html", ".json", ".txt"}


def chunk_text(text: str, max_chars: int = 1500) -> list[str]:
    paragraphs = text.split("\n\n")
    chunks, current = [], ""
    for para in paragraphs:
        if len(current) + len(para) > max_chars and current:
            chunks.append(current.strip())
            current = para
        else:
            current = f"{current}\n\n{para}" if current else para
    if current.strip():
        chunks.append(current.strip())
    return chunks


def index_directory(store: VectorStore, directory: Path, category: str) -> int:
    count = 0
    for f in directory.rglob("*"):
        if f.suffix not in INDEXABLE_EXTENSIONS or not f.is_file():
            continue
        try:
            text = f.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            continue
        for i, chunk in enumerate(chunk_text(text)):
            store.add(chunk, {
                "source": str(f.relative_to(ROOT)),
                "category": category,
                "chunk": i,
            })
            count += 1
    return count


def index_session(store: VectorStore, session_id: str) -> int:
    session_dir = get_session_dir(session_id)
    count = 0
    for subdir in ["wordpress", "source"]:
        d = session_dir / subdir
        if d.exists():
            count += index_directory(store, d, f"session:{session_id}/{subdir}")

    task_path = session_dir / "task.json"
    if task_path.exists():
        task = json.loads(task_path.read_text(encoding="utf-8"))
        notes = task.get("manifest", {}).get("notes", "")
        if notes:
            store.add(notes, {"source": f"session:{session_id}/notes", "category": "requirements"})
            count += 1
    return count


def main() -> int:
    parser = argparse.ArgumentParser(description="ナレッジベースインデックス作成")
    parser.add_argument("--session", help="セッションIDをインデックス")
    parser.add_argument("--rebuild", action="store_true", help="インデックスを再構築")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    store_path = get_knowledge_dir() / "vector_store"
    if args.rebuild and store_path.exists():
        import shutil
        shutil.rmtree(store_path)

    store = VectorStore(store_path)
    total = 0

    # 静的ナレッジ
    for subdir, category in [
        ("prompts", "prompts"),
        ("docs", "documentation"),
        ("docs/examples", "examples"),
    ]:
        d = ROOT / subdir
        if d.exists():
            total += index_directory(store, d, category)

    if args.session:
        total += index_session(store, args.session)

    result = {"indexed_chunks": total, "total_documents": store.count()}
    if args.json:
        print(json.dumps(result, indent=2))
    else:
        print(f"Indexed {total} chunks (total: {store.count()} documents)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
