"""intake マニフェスト検証のテストクラス"""

from __future__ import annotations

import json
from pathlib import Path

from validate_intake import validate_manifest  # noqa: E402


def _valid_manifest(files: list[dict] | None = None) -> dict:
    if files is None:
        files = [
            {"path": "hero.html", "role": "html", "description": "html"},
            {"path": "hero.css", "role": "css", "description": "css"},
        ]
    return {
        "version": "1.0",
        "source": {
            "tool": "codex",
            "generated_at": "2026-07-10T00:00:00+09:00",
        },
        "target": {"type": "block", "theme_slug": "custom-theme", "block_name": "hero"},
        "files": files,
        "notes": "test",
    }


class TestValidateManifest:
    def test_ok_when_files_exist(self, tmp_path: Path):
        (tmp_path / "hero.html").write_text("<h1/>", encoding="utf-8")
        (tmp_path / "hero.css").write_text(".x{}", encoding="utf-8")
        errors = validate_manifest(_valid_manifest(), tmp_path)
        assert errors == []

    def test_fails_on_missing_file(self, tmp_path: Path):
        errors = validate_manifest(_valid_manifest(), tmp_path)
        assert any("見つかりません" in e for e in errors)

    def test_fails_on_bad_version(self, tmp_path: Path):
        (tmp_path / "hero.html").write_text("x", encoding="utf-8")
        (tmp_path / "hero.css").write_text("x", encoding="utf-8")
        m = _valid_manifest()
        m["version"] = "9.9"
        errors = validate_manifest(m, tmp_path)
        assert any("バージョン" in e for e in errors)

    def test_fails_on_empty_files(self, tmp_path: Path):
        m = _valid_manifest(files=[])
        errors = validate_manifest(m, tmp_path)
        assert errors
        assert any("files" in e for e in errors)

    def test_fails_on_invalid_target_type(self, tmp_path: Path):
        (tmp_path / "hero.html").write_text("x", encoding="utf-8")
        (tmp_path / "hero.css").write_text("x", encoding="utf-8")
        m = _valid_manifest()
        m["target"]["type"] = "widget"
        errors = validate_manifest(m, tmp_path)
        assert any("target.type が不正" in e for e in errors)

    def test_fails_on_missing_role(self, tmp_path: Path):
        (tmp_path / "hero.html").write_text("x", encoding="utf-8")
        m = _valid_manifest(
            files=[{"path": "hero.html", "description": "no role"}],
        )
        errors = validate_manifest(m, tmp_path)
        assert any("role が未設定" in e for e in errors)

    def test_example_package_validates(self):
        root = Path(__file__).resolve().parents[1]
        example = root / "intake" / "example"
        if not example.exists():
            return
        manifest = json.loads((example / "manifest.json").read_text(encoding="utf-8"))
        errors = validate_manifest(manifest, example)
        assert errors == [], errors
