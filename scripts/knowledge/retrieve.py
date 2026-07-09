#!/usr/bin/env python3
"""RAG検索 — セッション向けコンテキスト生成"""

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))

from lib.config import get_knowledge_dir, get_session_dir  # noqa: E402
from knowledge.vector_store import VectorStore  # noqa: E402


def build_query(session_id: str) -> str:
    session_dir = get_session_dir(session_id)
    task_path = session_dir / "task.json"
    if not task_path.exists():
        return session_id

    task = json.loads(task_path.read_text(encoding="utf-8"))
    manifest = task.get("manifest", {})
    target = manifest.get("target", {})
    parts = [
        target.get("type", ""),
        target.get("block_name", ""),
        target.get("page_slug", ""),
        manifest.get("notes", ""),
        manifest.get("source", {}).get("prompt", ""),
    ]
    return " ".join(p for p in parts if p)


def format_context(results: list[dict]) -> str:
    if not results:
        return "（関連ナレッジなし）"
    sections = []
    for i, r in enumerate(results, 1):
        meta = r.get("metadata", {})
        sections.append(
            f"### 参考 {i} (score: {r.get('score', 0):.3f})\n"
            f"出典: {meta.get('source', 'unknown')} / {meta.get('category', '')}\n\n"
            f"{r.get('text', '')[:800]}"
        )
    return "\n\n---\n\n".join(sections)


def main() -> int:
    parser = argparse.ArgumentParser(description="RAGナレッジ検索")
    parser.add_argument("--session", required=True, help="セッションID")
    parser.add_argument("--query", help="検索クエリ（省略時はマニフェストから生成）")
    parser.add_argument("--top-k", type=int, default=5)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    store_path = get_knowledge_dir() / "vector_store"
    if not store_path.exists() or not (store_path / "index.json").exists():
        print("WARN: ナレッジベースが空です。先に index.py を実行してください", file=sys.stderr)
        # 空でも続行
        store = VectorStore(store_path)
    else:
        store = VectorStore(store_path)

    query = args.query or build_query(args.session)
    results = store.search(query, top_k=args.top_k)
    context = format_context(results)

    session_dir = get_session_dir(args.session)
    session_dir.mkdir(parents=True, exist_ok=True)
    (session_dir / "rag_context.md").write_text(context, encoding="utf-8")

    output = {
        "session_id": args.session,
        "query": query,
        "results_count": len(results),
        "context_file": str(session_dir / "rag_context.md"),
    }

    if args.json:
        print(json.dumps({**output, "results": results}, indent=2, ensure_ascii=False))
    else:
        print(f"RAG: {len(results)} results → {output['context_file']}")
        print(f"Query: {query}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
