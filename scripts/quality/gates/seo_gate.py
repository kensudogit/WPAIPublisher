#!/usr/bin/env python3
"""SEO品質ゲート"""

import re
from pathlib import Path

from .base import GateResult, collect_files, read_files


def check_seo(wp_dir: Path, rules: dict) -> GateResult:
    result = GateResult(gate="seo", passed=True, blocking=False)
    content = read_files(collect_files(wp_dir)["html"])

    if rules.get("require_title"):
        if not re.search(r"<title[^>]*>.+</title>", content, re.I | re.S):
            result.warnings.append("titleタグが見つかりません")

    if rules.get("require_meta_description"):
        if not re.search(r'<meta[^>]*name=["\']description["\']', content, re.I):
            result.warnings.append("meta descriptionが見つかりません")

    if rules.get("require_h1"):
        h1_count = len(re.findall(r"<h1[\s>]", content, re.I))
        if h1_count == 0:
            result.warnings.append("h1タグが見つかりません")
        max_h1 = rules.get("max_h1_count", 1)
        if h1_count > max_h1:
            result.warnings.append(f"h1が多すぎます: {h1_count} > {max_h1}")

    if rules.get("require_alt_on_images"):
        imgs = re.findall(r"<img[^>]*>", content, re.I)
        for img in imgs:
            if not re.search(r'alt\s*=\s*["\'][^"\']+["\']', img, re.I):
                result.warnings.append(f"alt属性のない画像: {img[:60]}...")

    if rules.get("require_canonical"):
        if not re.search(r'<link[^>]*rel=["\']canonical["\']', content, re.I):
            result.warnings.append("canonicalリンクが見つかりません")

    result.passed = len(result.warnings) == 0
    result.metrics = {"warnings_count": len(result.warnings)}
    return result
