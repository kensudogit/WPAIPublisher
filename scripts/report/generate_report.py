#!/usr/bin/env python3
"""変更内容レポート生成（structure / conversion / quality / visual / git / deploy）"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))

from lib.config import get_session_dir  # noqa: E402


def _load(path: Path) -> Any | None:
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return None


def _md_table(rows: list[tuple[str, str]]) -> str:
    lines = ["| 項目 | 内容 |", "|------|------|"]
    for k, v in rows:
        lines.append(f"| {k} | {v} |")
    return "\n".join(lines)


def generate_report(session_id: str) -> dict[str, Any]:
    session_dir = get_session_dir(session_id)
    task = _load(session_dir / "task.json") or {}
    structure = _load(session_dir / "structure.json") or {}
    conversion = _load(session_dir / "swell_conversion.json") or {}
    validation = _load(session_dir / "validation.json") or {}
    quality = _load(session_dir / "quality_gates.json") or {}
    visual = _load(session_dir / "visual_regression.json") or {}
    git_push = _load(session_dir / "git_push.json") or _load(session_dir / "git_pr.json") or {}
    agent = _load(session_dir / "agent_state.json") or {}

    target = (task.get("manifest") or {}).get("target") or {}
    source = (task.get("manifest") or {}).get("source") or {}

    wp_files: list[str] = []
    wp = session_dir / "wordpress"
    if wp.exists():
        wp_files = sorted(
            str(p.relative_to(wp)).replace("\\", "/")
            for p in wp.rglob("*")
            if p.is_file() and p.name != "preview.html"
        )

    visual_results = visual.get("results") or []
    visual_passed = visual.get("passed")
    quality_passed = quality.get("passed")
    if quality_passed is None and isinstance(quality.get("gates"), list):
        quality_passed = all(g.get("passed", True) for g in quality["gates"])

    report: dict[str, Any] = {
        "session_id": session_id,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "status": task.get("status", "unknown"),
        "engine": task.get("conversion_engine") or conversion.get("engine") or "unknown",
        "source": {
            "tool": source.get("tool"),
            "prompt": source.get("prompt"),
            "files": structure.get("source_files") or conversion.get("source_files") or [],
        },
        "target": target,
        "structure": {
            "title": structure.get("title"),
            "component_count": (structure.get("meta") or {}).get("component_count", 0),
            "routing": structure.get("routing") or {},
            "components": [
                {
                    "id": c.get("id"),
                    "kind": c.get("kind"),
                    "swell_target": c.get("swell_target"),
                    "confidence": c.get("confidence"),
                }
                for c in (structure.get("components") or [])[:50]
            ],
        },
        "conversion": {
            "theme_slug": conversion.get("theme_slug"),
            "parent_theme": conversion.get("parent_theme"),
            "blocks": conversion.get("blocks") or [],
            "template_parts": conversion.get("template_parts") or [],
            "page_slug": conversion.get("page_slug"),
        },
        "wordpress_files": wp_files,
        "validation": {
            "valid": validation.get("valid"),
            "checks": validation.get("checks") or validation.get("errors") or [],
        },
        "quality": {
            "passed": quality_passed,
            "summary": quality.get("summary") or quality.get("gates"),
        },
        "visual": {
            "passed": visual_passed,
            "base_url": visual.get("base_url"),
            "results": visual_results,
        },
        "git": {
            "branch": git_push.get("branch"),
            "pushed": git_push.get("pushed"),
            "pr_url": git_push.get("pr_url") or (git_push.get("pr") or {}).get("pr_url"),
            "deploy_path": git_push.get("deploy_path"),
        },
        "deploy": {
            "staging_url": task.get("staging_url"),
            "status": task.get("status"),
        },
        "agent": {
            "status": agent.get("status"),
            "completed_stages": agent.get("completed_stages"),
        },
    }

    # 総合判定
    flags = []
    if validation.get("valid") is False:
        flags.append("validation_failed")
    if quality_passed is False:
        flags.append("quality_failed")
    if visual_passed is False:
        flags.append("visual_failed")
    report["overall"] = "passed" if not flags else "attention"
    report["flags"] = flags

    # Markdown
    md_lines = [
        f"# 変更レポート: {session_id}",
        "",
        f"生成: {report['generated_at']}",
        f"総合: **{report['overall']}**" + (f" ({', '.join(flags)})" if flags else ""),
        "",
        "## 概要",
        _md_table(
            [
                ("Status", str(report["status"])),
                ("Engine", str(report["engine"])),
                ("Theme", str(target.get("theme_slug", "-"))),
                ("Parent", str(target.get("parent_theme", "-"))),
                ("Page slug", str(target.get("page_slug") or conversion.get("page_slug") or "-")),
                ("Source AI", str(source.get("tool", "-"))),
            ]
        ),
        "",
        "## HTML 解析",
        f"- タイトル: {structure.get('title') or '-'}",
        f"- コンポーネント数: {(structure.get('meta') or {}).get('component_count', 0)}",
        "",
    ]
    routing = structure.get("routing") or {}
    if routing:
        md_lines.append("### SWELL 振り分け")
        for k, ids in routing.items():
            if ids:
                md_lines.append(f"- `{k}`: {len(ids)} 件")
        md_lines.append("")

    if report["structure"]["components"]:
        md_lines.append("### コンポーネント")
        md_lines.append("| ID | Kind | Target | Conf |")
        md_lines.append("|----|------|--------|------|")
        for c in report["structure"]["components"][:30]:
            md_lines.append(
                f"| {c['id']} | {c['kind']} | {c['swell_target']} | {c.get('confidence', '')} |"
            )
        md_lines.append("")

    md_lines.extend(
        [
            "## 変換結果",
            f"- Blocks: {', '.join(conversion.get('blocks') or []) or '-'}",
            f"- Template parts: {', '.join(conversion.get('template_parts') or []) or '-'}",
            f"- 出力ファイル数: {len(wp_files)}",
            "",
        ]
    )
    if wp_files:
        md_lines.append("<details><summary>wordpress/ ファイル一覧</summary>")
        md_lines.append("")
        for f in wp_files:
            md_lines.append(f"- `{f}`")
        md_lines.append("")
        md_lines.append("</details>")
        md_lines.append("")

    md_lines.extend(
        [
            "## 品質・表示確認",
            _md_table(
                [
                    ("Validation", "OK" if validation.get("valid") else str(validation.get("valid"))),
                    ("Quality gates", "OK" if quality_passed else str(quality_passed)),
                    ("Visual regression", "OK" if visual_passed else str(visual_passed)),
                    ("Visual URL", str(visual.get("base_url") or "-")),
                ]
            ),
            "",
        ]
    )
    if visual_results:
        md_lines.append("### Viewport")
        for r in visual_results:
            mark = "OK" if r.get("passed") else "NG"
            extra = r.get("action") or r.get("diffPercent") or r.get("diffBytes") or ""
            md_lines.append(f"- [{mark}] {r.get('viewport')} {extra}")
        md_lines.append("")

    md_lines.extend(
        [
            "## Git / Deploy",
            _md_table(
                [
                    ("Branch", str(git_push.get("branch") or "-")),
                    ("Pushed", str(git_push.get("pushed"))),
                    ("PR", str(report["git"].get("pr_url") or "-")),
                    ("Deploy path", str(git_push.get("deploy_path") or "-")),
                    ("Staging URL", str(task.get("staging_url") or "-")),
                ]
            ),
            "",
            "---",
            "_Generated by WPAIPublisher_",
        ]
    )

    md = "\n".join(md_lines)
    (session_dir / "change_report.json").write_text(
        json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    (session_dir / "change_report.md").write_text(md, encoding="utf-8")
    report["markdown_path"] = str(session_dir / "change_report.md")
    report["json_path"] = str(session_dir / "change_report.json")
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description="変更レポート生成")
    parser.add_argument("session_id")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    report = generate_report(args.session_id)
    if args.json:
        print(json.dumps(report, indent=2, ensure_ascii=False))
    else:
        print(f"Report: {report['markdown_path']}")
        print(f"Overall: {report['overall']}")
        print(f"Files: {len(report.get('wordpress_files') or [])}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
