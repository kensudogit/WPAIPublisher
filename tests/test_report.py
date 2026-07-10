"""変更レポート生成のテスト"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from report.generate_report import generate_report


class TestGenerateReport:
    def test_writes_md_and_json(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
        session = tmp_path / "r1"
        session.mkdir()
        (session / "task.json").write_text(
            json.dumps(
                {
                    "status": "converted",
                    "conversion_engine": "swell",
                    "manifest": {
                        "source": {"tool": "other"},
                        "target": {
                            "type": "page",
                            "theme_slug": "swell-child",
                            "parent_theme": "swell",
                            "page_slug": "home",
                        },
                    },
                }
            ),
            encoding="utf-8",
        )
        (session / "structure.json").write_text(
            json.dumps(
                {
                    "title": "Home",
                    "meta": {"component_count": 1},
                    "routing": {"block": ["c001-hero"]},
                    "components": [
                        {
                            "id": "c001-hero",
                            "kind": "hero",
                            "swell_target": "block",
                            "confidence": 0.9,
                        }
                    ],
                }
            ),
            encoding="utf-8",
        )
        wp = session / "wordpress"
        wp.mkdir()
        (wp / "style.css").write_text("x", encoding="utf-8")

        monkeypatch.setattr("report.generate_report.get_session_dir", lambda sid: session)
        report = generate_report("r1")
        assert report["overall"] in {"passed", "attention"}
        assert (session / "change_report.md").exists()
        assert (session / "change_report.json").exists()
        md = (session / "change_report.md").read_text(encoding="utf-8")
        assert "変更レポート" in md
        assert "swell-child" in md
