#!/usr/bin/env python3
"""HTML 解析: ページ構造・コンポーネント抽出"""

from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import asdict, dataclass, field
from html.parser import HTMLParser
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))

from lib.config import get_session_dir  # noqa: E402

SECTION_TAGS = {"header", "nav", "main", "section", "article", "aside", "footer", "form"}
COMPONENT_HINTS = {
    "hero": ["hero", "mv", "main-visual", "jumbotron", "banner"],
    "nav": ["nav", "menu", "gnav", "header-nav"],
    "cta": ["cta", "call-to-action", "btn-area", "action"],
    "card": ["card", "cards", "feature", "service"],
    "faq": ["faq", "accordion", "qa"],
    "gallery": ["gallery", "slider", "carousel", "swiper"],
    "contact": ["contact", "form", "inquiry"],
    "footer": ["footer", "site-footer"],
    "pricing": ["price", "pricing", "plan"],
    "testimonial": ["voice", "review", "testimonial", "customer"],
}


@dataclass
class Component:
    id: str
    kind: str
    tag: str
    classes: list[str]
    id_attr: str | None
    text_preview: str
    children_count: int
    swell_target: str  # block | template-part | page-content | child-theme-asset
    confidence: float


@dataclass
class StructureReport:
    source_files: list[str] = field(default_factory=list)
    title: str | None = None
    headings: list[dict[str, Any]] = field(default_factory=list)
    sections: list[dict[str, Any]] = field(default_factory=list)
    components: list[dict[str, Any]] = field(default_factory=list)
    assets: dict[str, list[str]] = field(default_factory=lambda: {"css": [], "js": [], "images": []})
    meta: dict[str, Any] = field(default_factory=dict)
    routing: dict[str, list[str]] = field(default_factory=dict)


class StructureParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.title: str | None = None
        self._in_title = False
        self.headings: list[dict[str, Any]] = []
        self.sections: list[dict[str, Any]] = []
        self.components: list[Component] = []
        self.assets: dict[str, list[str]] = {"css": [], "js": [], "images": []}
        self._stack: list[dict[str, Any]] = []
        self._comp_counter = 0
        self._text_buf: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        attr = {k: (v or "") for k, v in attrs}
        classes = [c for c in attr.get("class", "").split() if c]
        el_id = attr.get("id") or None

        if tag == "title":
            self._in_title = True
        if tag == "link" and "stylesheet" in attr.get("rel", ""):
            href = attr.get("href")
            if href:
                self.assets["css"].append(href)
        if tag == "script" and attr.get("src"):
            self.assets["js"].append(attr["src"])
        if tag == "img" and attr.get("src"):
            self.assets["images"].append(attr["src"])

        if tag in {"h1", "h2", "h3", "h4", "h5", "h6"}:
            self._stack.append({"tag": tag, "classes": classes, "id": el_id, "text": []})
            return

        if tag in SECTION_TAGS or self._looks_like_component(classes, el_id):
            kind = self._classify(tag, classes, el_id)
            self._comp_counter += 1
            node = {
                "tag": tag,
                "classes": classes,
                "id": el_id,
                "kind": kind,
                "text": [],
                "children": 0,
                "depth": len(self._stack),
            }
            self._stack.append(node)
            if self._stack and len(self._stack) > 1:
                self._stack[-2]["children"] = self._stack[-2].get("children", 0) + 1

    def handle_endtag(self, tag: str) -> None:
        if tag == "title":
            self._in_title = False
            return
        if not self._stack:
            return
        top = self._stack[-1]
        if top.get("tag") != tag and tag not in SECTION_TAGS and tag not in {"h1", "h2", "h3", "h4", "h5", "h6"}:
            return
        if top.get("tag") != tag:
            return
        node = self._stack.pop()
        text = " ".join(node.get("text", [])).strip()
        text = re.sub(r"\s+", " ", text)[:160]

        if tag in {"h1", "h2", "h3", "h4", "h5", "h6"}:
            self.headings.append({"level": int(tag[1]), "text": text, "id": node.get("id")})
            return

        kind = node.get("kind", "section")
        swell_target, confidence = route_to_swell(kind, tag, node.get("classes") or [])
        comp = Component(
            id=f"c{self._comp_counter:03d}-{kind}",
            kind=kind,
            tag=tag,
            classes=node.get("classes") or [],
            id_attr=node.get("id"),
            text_preview=text,
            children_count=int(node.get("children") or 0),
            swell_target=swell_target,
            confidence=confidence,
        )
        self.components.append(comp)
        self.sections.append(
            {
                "id": comp.id,
                "kind": kind,
                "tag": tag,
                "classes": comp.classes,
                "swell_target": swell_target,
            }
        )

    def handle_data(self, data: str) -> None:
        text = data.strip()
        if not text:
            return
        if self._in_title:
            self.title = (self.title or "") + text
        if self._stack:
            self._stack[-1].setdefault("text", []).append(text)

    def _looks_like_component(self, classes: list[str], el_id: str | None) -> bool:
        blob = " ".join(classes + ([el_id] if el_id else [])).lower()
        return any(h in blob for hints in COMPONENT_HINTS.values() for h in hints)

    def _classify(self, tag: str, classes: list[str], el_id: str | None) -> str:
        blob = " ".join(classes + ([el_id] if el_id else []) + [tag]).lower()
        for kind, hints in COMPONENT_HINTS.items():
            if any(h in blob for h in hints):
                return kind
        if tag == "header":
            return "header"
        if tag == "footer":
            return "footer"
        if tag == "nav":
            return "nav"
        if tag == "form":
            return "contact"
        if tag == "main":
            return "main"
        return "section"


def route_to_swell(kind: str, tag: str, classes: list[str]) -> tuple[str, float]:
    """コンポーネント種別 → SWELL 振り分け先"""
    if kind in {"nav", "header", "footer"}:
        return "template-part", 0.9
    if kind in {"hero", "cta", "card", "faq", "gallery", "pricing", "testimonial"}:
        return "block", 0.85
    if kind == "contact":
        return "block", 0.8
    if kind == "main":
        return "page-content", 0.75
    if any(c.startswith("l-") or c.startswith("c-") or c.startswith("p-") for c in classes):
        return "child-theme-asset", 0.7
    if tag in {"section", "article"}:
        return "block", 0.65
    return "page-content", 0.5


def analyze_html_file(path: Path) -> StructureParser:
    parser = StructureParser()
    text = path.read_text(encoding="utf-8", errors="ignore")
    parser.feed(text)
    return parser


def analyze_paths(paths: list[Path]) -> StructureReport:
    report = StructureReport()
    for path in paths:
        if not path.exists() or path.suffix.lower() not in {".html", ".htm"}:
            continue
        report.source_files.append(str(path))
        parsed = analyze_html_file(path)
        if parsed.title and not report.title:
            report.title = parsed.title
        report.headings.extend(parsed.headings)
        report.sections.extend(parsed.sections)
        report.components.extend([asdict(c) for c in parsed.components])
        for k in ("css", "js", "images"):
            for item in parsed.assets[k]:
                if item not in report.assets[k]:
                    report.assets[k].append(item)

    routing: dict[str, list[str]] = {
        "block": [],
        "template-part": [],
        "page-content": [],
        "child-theme-asset": [],
    }
    for c in report.components:
        routing.setdefault(c["swell_target"], []).append(c["id"])
    report.routing = routing
    report.meta = {
        "component_count": len(report.components),
        "heading_count": len(report.headings),
        "section_count": len(report.sections),
    }
    return report


def analyze_session(session_id: str) -> StructureReport:
    session_dir = get_session_dir(session_id)
    source = session_dir / "source"
    html_files = sorted(source.rglob("*.html")) if source.exists() else []
    if not html_files:
        # intake 直下や wordpress 前のフォールバック
        html_files = sorted(session_dir.rglob("*.html"))
        html_files = [p for p in html_files if "visual" not in p.parts and "preview" not in p.name]
    report = analyze_paths(html_files)
    out = session_dir / "structure.json"
    out.write_text(json.dumps(asdict(report), indent=2, ensure_ascii=False), encoding="utf-8")
    return report


def analyze_directory(source_dir: Path, out_path: Path | None = None) -> StructureReport:
    html_files = sorted(source_dir.rglob("*.html"))
    report = analyze_paths(html_files)
    if out_path:
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(json.dumps(asdict(report), indent=2, ensure_ascii=False), encoding="utf-8")
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description="HTML 構造・コンポーネント解析")
    parser.add_argument("target", help="セッションID または HTML フォルダ")
    parser.add_argument("--out", help="出力 JSON パス")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    target = Path(args.target)
    if target.exists() and target.is_dir():
        out = Path(args.out) if args.out else target / "structure.json"
        report = analyze_directory(target, out)
    else:
        report = analyze_session(args.target)
        out = get_session_dir(args.target) / "structure.json"

    data = asdict(report)
    if args.json:
        print(json.dumps(data, indent=2, ensure_ascii=False))
    else:
        print(f"Analyzed: {len(report.source_files)} HTML file(s)")
        print(f"Title: {report.title or '(none)'}")
        print(f"Components: {report.meta.get('component_count', 0)}")
        for target_name, ids in report.routing.items():
            if ids:
                print(f"  → {target_name}: {len(ids)}")
        print(f"Saved: {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
