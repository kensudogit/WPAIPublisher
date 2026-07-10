"""SWELL 変換のテスト"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from swell.convert_to_swell import convert_session, extract_body, write_child_theme_scaffold


class TestExtractBody:
    def test_extracts_inner_body(self):
        html = "<html><head><title>t</title></head><body><h1>Hi</h1></body></html>"
        assert "<h1>Hi</h1>" in extract_body(html)


class TestChildThemeScaffold:
    def test_writes_style_and_functions(self, tmp_path: Path):
        dest = tmp_path / "theme"
        write_child_theme_scaffold(dest, "swell-child", "swell")
        style = (dest / "style.css").read_text(encoding="utf-8")
        assert "Template: swell" in style
        assert (dest / "functions.php").exists()
        assert (dest / "blocks").is_dir()


class TestConvertSession:
    def test_converts_source_html(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
        session = tmp_path / "sess1"
        source = session / "source"
        source.mkdir(parents=True)
        (source / "hero.html").write_text(
            "<html><body><section class='hero'><h1>Hero</h1></section></body></html>",
            encoding="utf-8",
        )
        (source / "hero.css").write_text(".hero{color:red}", encoding="utf-8")
        task = {
            "status": "pending_conversion",
            "manifest": {
                "source": {"tool": "other"},
                "target": {"type": "page", "theme_slug": "swell-child", "page_slug": "hero"},
                "files": [{"path": "hero.html", "role": "html"}],
            },
        }
        (session / "task.json").write_text(json.dumps(task), encoding="utf-8")

        monkeypatch.setattr(
            "swell.convert_to_swell.get_session_dir",
            lambda sid: session,
        )
        monkeypatch.setattr(
            "analyze.html_structure.get_session_dir",
            lambda sid: session,
        )

        result = convert_session("sess1", theme_slug="swell-child", parent_theme="swell")
        assert result["theme_slug"] == "swell-child"
        assert "hero" in result["blocks"]
        assert (session / "wordpress" / "style.css").exists()
        assert (session / "wordpress" / "blocks" / "hero" / "block.json").exists()
        assert (session / "swell_conversion.json").exists()
        assert (session / "validation.json").exists()
