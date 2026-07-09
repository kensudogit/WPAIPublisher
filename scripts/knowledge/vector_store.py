#!/usr/bin/env python3
"""ベクトルストア（ローカルJSON + TF-IDF、オプションでChromaDB）"""

import hashlib
import json
import math
import re
from collections import Counter
from pathlib import Path
from typing import Any


class VectorStore:
    def __init__(self, store_path: Path):
        self.store_path = store_path
        self.store_path.mkdir(parents=True, exist_ok=True)
        self.index_file = store_path / "index.json"
        self.documents: list[dict] = self._load()

    def _load(self) -> list[dict]:
        if self.index_file.exists():
            return json.loads(self.index_file.read_text(encoding="utf-8"))
        return []

    def _save(self) -> None:
        self.index_file.write_text(
            json.dumps(self.documents, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )

    @staticmethod
    def _tokenize(text: str) -> list[str]:
        tokens = re.findall(r"[a-zA-Z_][a-zA-Z0-9_]*|[\u3040-\u30ff\u4e00-\u9fff]+|\d+", text.lower())
        return [t for t in tokens if len(t) > 1]

    @staticmethod
    def _tfidf_vector(tokens: list[str], idf: dict[str, float]) -> dict[str, float]:
        tf = Counter(tokens)
        total = len(tokens) or 1
        return {t: (count / total) * idf.get(t, 1.0) for t, count in tf.items()}

    def _compute_idf(self) -> dict[str, float]:
        n = len(self.documents) or 1
        df: Counter = Counter()
        for doc in self.documents:
            tokens = set(self._tokenize(doc.get("text", "")))
            for t in tokens:
                df[t] += 1
        return {t: math.log(n / (df_val + 1)) + 1 for t, df_val in df.items()}

    @staticmethod
    def _cosine_similarity(v1: dict[str, float], v2: dict[str, float]) -> float:
        common = set(v1) & set(v2)
        if not common:
            return 0.0
        dot = sum(v1[t] * v2[t] for t in common)
        norm1 = math.sqrt(sum(x * x for x in v1.values()))
        norm2 = math.sqrt(sum(x * x for x in v2.values()))
        return dot / (norm1 * norm2) if norm1 and norm2 else 0.0

    def add(self, text: str, metadata: dict[str, Any]) -> str:
        doc_id = hashlib.sha256(text.encode()).hexdigest()[:16]
        existing = {d["id"] for d in self.documents}
        if doc_id in existing:
            return doc_id
        self.documents.append({
            "id": doc_id,
            "text": text,
            "metadata": metadata,
        })
        self._save()
        return doc_id

    def search(self, query: str, top_k: int = 5) -> list[dict]:
        if not self.documents:
            return []
        idf = self._compute_idf()
        query_vec = self._tfidf_vector(self._tokenize(query), idf)
        results = []
        for doc in self.documents:
            doc_vec = self._tfidf_vector(self._tokenize(doc["text"]), idf)
            score = self._cosine_similarity(query_vec, doc_vec)
            results.append({**doc, "score": score})
        results.sort(key=lambda x: x["score"], reverse=True)
        return results[:top_k]

    def count(self) -> int:
        return len(self.documents)
