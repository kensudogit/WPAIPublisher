#!/usr/bin/env python3
"""パフォーマンス品質ゲート"""

from pathlib import Path

from .base import GateResult, collect_files


def check_performance(wp_dir: Path, rules: dict) -> GateResult:
    result = GateResult(gate="performance", passed=True, blocking=False)

    files = collect_files(wp_dir)
    css_size = sum(f.stat().st_size for f in files["css"]) / 1024
    js_size = sum(f.stat().st_size for f in files["js"]) / 1024

    max_css = rules.get("max_css_size_kb", 100)
    max_js = rules.get("max_js_size_kb", 50)

    if css_size > max_css:
        result.warnings.append(f"CSSサイズ超過: {css_size:.1f}KB > {max_css}KB")
    if js_size > max_js:
        result.warnings.append(f"JSサイズ超過: {js_size:.1f}KB > {max_js}KB")

    inline_scripts = 0
    for f in files["html"]:
        content = f.read_text(encoding="utf-8", errors="ignore")
        inline_scripts += content.lower().count("<script")

    max_inline = rules.get("max_inline_scripts", 3)
    if inline_scripts > max_inline:
        result.warnings.append(f"インラインscript過多: {inline_scripts} > {max_inline}")

    result.metrics = {"css_kb": round(css_size, 1), "js_kb": round(js_size, 1), "inline_scripts": inline_scripts}
    result.passed = len(result.warnings) == 0
    return result
