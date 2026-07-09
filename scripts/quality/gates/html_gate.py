#!/usr/bin/env python3
"""HTML品質ゲート"""

import re
from pathlib import Path

from .base import GateResult, collect_files, read_files


def check_html(wp_dir: Path, rules: dict) -> GateResult:
    result = GateResult(gate="html", passed=True, blocking=True)
    files = collect_files(wp_dir)
    html_content = read_files(files["html"])

    if not html_content.strip():
        result.warnings.append("HTML/PHPコンテンツが空です")
        return result

    if rules.get("require_lang"):
        if not re.search(r'<html[^>]*\slang=', html_content, re.I) and "<!DOCTYPE" in html_content:
            result.errors.append("html要素にlang属性がありません")

    forbidden = rules.get("forbidden_tags", [])
    for tag in forbidden:
        if re.search(rf"<{tag}[\s>]", html_content, re.I):
            result.errors.append(f"禁止タグが検出されました: <{tag}>")

    max_inline = rules.get("max_inline_styles", 10)
    inline_count = len(re.findall(r'style\s*=', html_content, re.I))
    if inline_count > max_inline:
        result.warnings.append(f"インラインスタイルが多すぎます: {inline_count} > {max_inline}")

    unclosed_imgs = len(re.findall(r"<img[^>]*(?<!/)>", html_content, re.I))
    if unclosed_imgs:
        result.warnings.append(f"自己閉じでないimgタグ: {unclosed_imgs}件")

    result.passed = len(result.errors) == 0
    result.metrics = {"inline_styles": inline_count, "files_checked": len(files["html"])}
    return result
