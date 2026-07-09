#!/usr/bin/env python3
"""アクセシビリティ品質ゲート"""

import re
import shutil
import subprocess
from pathlib import Path

from .base import GateResult, collect_files, read_files


def check_accessibility(wp_dir: Path, rules: dict) -> GateResult:
    result = GateResult(gate="accessibility", passed=True, blocking=True)
    content = read_files(collect_files(wp_dir)["html"])
    html_files = [f for f in collect_files(wp_dir)["html"] if f.suffix == ".html"]

    if rules.get("require_alt"):
        imgs = re.findall(r"<img[^>]*>", content, re.I)
        missing_alt = [img for img in imgs if not re.search(r'alt\s*=', img, re.I)]
        if missing_alt:
            result.errors.append(f"alt属性のない画像: {len(missing_alt)}件")

    if rules.get("require_form_labels"):
        inputs = re.findall(r"<input[^>]*>", content, re.I)
        for inp in inputs:
            if re.search(r'type\s*=\s*["\']hidden["\']', inp, re.I):
                continue
            has_aria = re.search(r'aria-label\s*=', inp, re.I)
            has_id = re.search(r'id\s*=\s*["\']([^"\']+)["\']', inp, re.I)
            has_label = False
            if has_id:
                input_id = has_id.group(1)
                has_label = bool(re.search(rf'<label[^>]*for\s*=\s*["\']' + re.escape(input_id), content, re.I))
            if not has_aria and not has_label:
                result.warnings.append(f"ラベルのないinput: {inp[:50]}...")

    buttons = re.findall(r"<button[^>]*>", content, re.I)
    for btn in buttons:
        if not re.search(r">.+<", btn) and not re.search(r'aria-label\s*=', btn, re.I):
            result.warnings.append("テキスト/aria-labelのないbutton")

    # axe-core CLI（Node.js、インストール済みの場合）
    tools = rules.get("tools", [])
    if "axe" in tools and html_files and shutil.which("npx"):
        for html_file in html_files[:3]:
            axe_result = _run_axe(html_file)
            result.errors.extend(axe_result.get("errors", []))
            result.warnings.extend(axe_result.get("warnings", []))

    result.passed = len(result.errors) == 0
    return result


def _run_axe(html_file: Path) -> dict:
    try:
        result = subprocess.run(
            ["npx", "@axe-core/cli", str(html_file), "--exit"],
            capture_output=True,
            text=True,
            timeout=60,
        )
        if result.returncode != 0:
            return {"errors": [f"axe違反: {html_file.name} - {result.stdout[:200]}"]}
    except (subprocess.TimeoutExpired, FileNotFoundError):
        pass
    return {}
