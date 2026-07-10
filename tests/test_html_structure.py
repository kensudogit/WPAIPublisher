"""HTML 構造解析のテスト"""

from __future__ import annotations

from pathlib import Path

from analyze.html_structure import analyze_paths, route_to_swell


class TestRouteToSwell:
    def test_route_hero_to_block(self):
        target, conf = route_to_swell("hero", "section", ["hero"])
        assert target == "block"
        assert conf >= 0.8

    def test_route_nav_to_template_part(self):
        target, conf = route_to_swell("nav", "nav", ["gnav"])
        assert target == "template-part"


class TestAnalyzePaths:
    def test_analyze_extracts_components(self, tmp_path: Path):
        html = tmp_path / "page.html"
        html.write_text(
            """<!DOCTYPE html><html><head><title>Demo</title>
<link rel="stylesheet" href="a.css">
</head><body>
<header class="site-header"><nav class="gnav">Menu</nav></header>
<section class="hero"><h1>Welcome</h1><p>Lead</p></section>
<footer class="site-footer">Foot</footer>
</body></html>""",
            encoding="utf-8",
        )
        report = analyze_paths([html])
        assert report.title == "Demo"
        assert report.meta["component_count"] >= 2
        kinds = {c["kind"] for c in report.components}
        assert "hero" in kinds or "header" in kinds or "nav" in kinds
        assert report.assets["css"]
