#!/usr/bin/env python3
"""品質ゲート共通ユーティリティ"""

import re
from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class GateResult:
    gate: str
    passed: bool
    blocking: bool
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    metrics: dict = field(default_factory=dict)


def collect_files(wp_dir: Path) -> dict[str, list[Path]]:
    return {
        "html": list(wp_dir.rglob("*.html")) + list(wp_dir.rglob("*.php")),
        "css": list(wp_dir.rglob("*.css")),
        "js": list(wp_dir.rglob("*.js")),
        "php": list(wp_dir.rglob("*.php")),
        "all": [f for f in wp_dir.rglob("*") if f.is_file()],
    }


def read_files(files: list[Path]) -> str:
    parts = []
    for f in files:
        try:
            parts.append(f.read_text(encoding="utf-8", errors="ignore"))
        except OSError:
            pass
    return "\n".join(parts)


def count_pattern(text: str, pattern: str) -> int:
    return len(re.findall(pattern, text, re.IGNORECASE))
