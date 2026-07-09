#!/usr/bin/env python3
"""セキュリティ品質ゲート"""

import re
from pathlib import Path

from .base import GateResult, collect_files


def check_security(wp_dir: Path, rules: dict) -> GateResult:
    result = GateResult(gate="security", passed=True, blocking=True)
    files = collect_files(wp_dir)

    forbidden_funcs = rules.get("forbidden_functions", [])
    forbidden_patterns = rules.get("forbidden_patterns", [])

    for f in files["php"] + files["js"]:
        try:
            content = f.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            continue

        for func in forbidden_funcs:
            if re.search(rf"\b{re.escape(func)}\s*\(", content):
                result.errors.append(f"{f.relative_to(wp_dir)}: 禁止関数 {func}()")

        for pattern in forbidden_patterns:
            if re.search(pattern, content):
                result.errors.append(f"{f.relative_to(wp_dir)}: 禁止パターン {pattern}")

        if f.suffix == ".php" and rules.get("require_escaping"):
            echo_patterns = re.findall(r"echo\s+\$_(?:GET|POST|REQUEST)", content)
            if echo_patterns:
                result.errors.append(f"{f.relative_to(wp_dir)}: 未エスケープのスーパーグローバル出力")

    result.passed = len(result.errors) == 0
    result.metrics = {"files_scanned": len(files["php"]) + len(files["js"])}
    return result
