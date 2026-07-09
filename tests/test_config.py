"""設定ヘルパーのテストクラス"""

from __future__ import annotations

from pathlib import Path

from lib import config


class TestConfigHelpers:
    def test_load_env_file_parses_keys(self, tmp_path: Path):
        env = tmp_path / ".env"
        env.write_text(
            "# comment\nWP_STAGING_URL=https://example.test\nEMPTY=\n",
            encoding="utf-8",
        )
        data = config.load_env_file(env)
        assert data["WP_STAGING_URL"] == "https://example.test"
        assert data["EMPTY"] == ""

    def test_load_env_file_missing_returns_empty(self, tmp_path: Path):
        assert config.load_env_file(tmp_path / "nope.env") == {}

    def test_get_output_and_intake_dirs(self):
        assert config.get_output_dir().name == "output"
        assert config.get_intake_dir().name == "intake"

    def test_get_session_dir(self):
        path = config.get_session_dir("demo-session")
        assert path.name == "demo-session"
        assert path.parent == config.get_output_dir()
