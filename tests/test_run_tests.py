"""テストランナー自身のユーティリティテスト"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

# scripts/test を import できるように
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts" / "test"))

from run_tests import list_reports, load_report, summarize  # noqa: E402


class TestSummarize:
    def test_counts_outcomes(self):
        tests = [
            {"outcome": "passed"},
            {"outcome": "passed"},
            {"outcome": "failed"},
            {"outcome": "skipped"},
            {"outcome": "error"},
        ]
        s = summarize(tests)
        assert s == {"passed": 2, "failed": 1, "skipped": 1, "errors": 1, "total": 5}


class TestReportIO:
    def test_list_and_load(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
        monkeypatch.setattr("run_tests.RESULTS_DIR", tmp_path)
        report = {
            "id": "run-1",
            "status": "passed",
            "summary": {"passed": 1, "failed": 0, "skipped": 0, "errors": 0, "total": 1},
            "started_at": "2026-07-10T00:00:00+00:00",
            "finished_at": "2026-07-10T00:00:01+00:00",
            "duration_sec": 1.0,
            "tests": [],
        }
        (tmp_path / "run-1.json").write_text(json.dumps(report), encoding="utf-8")
        (tmp_path / "latest.json").write_text(json.dumps(report), encoding="utf-8")

        rows = list_reports()
        assert len(rows) == 1
        assert rows[0]["id"] == "run-1"

        loaded = load_report("latest")
        assert loaded is not None
        assert loaded["id"] == "run-1"
