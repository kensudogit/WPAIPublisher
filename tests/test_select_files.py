"""intake 選択・マニフェスト生成のテストクラス"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from select_files import (  # noqa: E402
    create_package,
    find_companions,
    list_html_files,
    slugify,
)


class TestSlugify:
    def test_simple_name(self):
        assert slugify("Hero Section.html") == "hero-section"

    def test_empty_fallback(self):
        assert slugify("@@@.html") == "page"

    def test_keeps_underscore(self):
        assert slugify("my_page.html") == "my_page"


class TestListHtmlFiles:
    def test_lists_nested_html(self, tmp_path: Path):
        (tmp_path / "a.html").write_text("<html></html>", encoding="utf-8")
        nested = tmp_path / "pages"
        nested.mkdir()
        (nested / "b.html").write_text("<html></html>", encoding="utf-8")
        (tmp_path / "readme.txt").write_text("x", encoding="utf-8")

        files = list_html_files(tmp_path)
        paths = [f["path"] for f in files]
        assert paths == ["a.html", "pages/b.html"]

    def test_detects_same_name_companions(self, tmp_path: Path):
        (tmp_path / "hero.html").write_text("<html></html>", encoding="utf-8")
        (tmp_path / "hero.css").write_text(".x{}", encoding="utf-8")
        (tmp_path / "hero.js").write_text("1", encoding="utf-8")

        files = list_html_files(tmp_path)
        assert len(files) == 1
        comps = files[0]["companions"]
        assert "hero.css" in comps
        assert "hero.js" in comps

    def test_detects_relative_asset_refs(self, tmp_path: Path):
        assets = tmp_path / "assets"
        assets.mkdir()
        (assets / "common.css").write_text("body{}", encoding="utf-8")
        (tmp_path / "page.html").write_text(
            '<link rel="stylesheet" href="assets/common.css">',
            encoding="utf-8",
        )

        comps = find_companions(tmp_path, tmp_path / "page.html")
        assert any(p.name == "common.css" for p in comps)

    def test_ignores_external_urls(self, tmp_path: Path):
        (tmp_path / "page.html").write_text(
            '<script src="https://cdn.example.com/a.js"></script>',
            encoding="utf-8",
        )
        comps = find_companions(tmp_path, tmp_path / "page.html")
        assert comps == []


class TestCreatePackage:
    def test_creates_manifest_and_copies_files(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
        intake_root = tmp_path / "intake"
        (intake_root / "incoming").mkdir(parents=True)
        monkeypatch.setattr("select_files.get_intake_dir", lambda: intake_root)

        src = tmp_path / "src"
        src.mkdir()
        (src / "hero.html").write_text("<h1>Hero</h1>", encoding="utf-8")
        (src / "hero.css").write_text(".hero{}", encoding="utf-8")

        dest = create_package(
            src,
            ["hero.html"],
            package_name="test-pkg",
            target_type="page",
            theme_slug="custom-theme",
            tool="other",
            notes="unit-test",
        )

        assert dest.name == "test-pkg"
        assert (dest / "hero.html").exists()
        assert (dest / "hero.css").exists()
        manifest = json.loads((dest / "manifest.json").read_text(encoding="utf-8"))
        assert manifest["version"] == "1.0"
        assert manifest["target"]["type"] == "page"
        roles = {f["path"]: f["role"] for f in manifest["files"]}
        assert roles["hero.html"] == "html"
        assert roles["hero.css"] == "css"

    def test_rejects_empty_selection(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
        intake_root = tmp_path / "intake"
        (intake_root / "incoming").mkdir(parents=True)
        monkeypatch.setattr("select_files.get_intake_dir", lambda: intake_root)
        src = tmp_path / "src"
        src.mkdir()
        with pytest.raises(ValueError, match="選択されていません"):
            create_package(src, [])

    def test_rejects_missing_html(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
        intake_root = tmp_path / "intake"
        (intake_root / "incoming").mkdir(parents=True)
        monkeypatch.setattr("select_files.get_intake_dir", lambda: intake_root)
        src = tmp_path / "src"
        src.mkdir()
        with pytest.raises(FileNotFoundError):
            create_package(src, ["missing.html"])
