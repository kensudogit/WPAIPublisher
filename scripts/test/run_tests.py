#!/usr/bin/env python3
"""pytest 実行 → JSON レポート保存（Web から参照）"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
RESULTS_DIR = ROOT / "output" / "test-results"


def _ensure_pytest() -> str | None:
    try:
        import pytest  # noqa: F401

        return None
    except ImportError:
        return "pytest が未インストールです。pip install pytest を実行してください。"


def run_tests(
    *,
    path: str = "tests",
    keyword: str | None = None,
    run_id: str | None = None,
) -> dict:
    err = _ensure_pytest()
    if err:
        return {
            "id": run_id or "error",
            "status": "error",
            "summary": {"passed": 0, "failed": 0, "skipped": 0, "errors": 1, "total": 0},
            "error": err,
            "tests": [],
            "started_at": datetime.now(timezone.utc).isoformat(),
            "finished_at": datetime.now(timezone.utc).isoformat(),
            "duration_sec": 0,
        }

    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    run_id = run_id or datetime.now().strftime("%Y%m%d-%H%M%S") + "-" + uuid.uuid4().hex[:6]
    junit_path = RESULTS_DIR / f"{run_id}.junit.xml"
    report_path = RESULTS_DIR / f"{run_id}.json"

    started = datetime.now(timezone.utc)
    cmd = [
        sys.executable,
        "-m",
        "pytest",
        path,
        "-v",
        "--tb=short",
        f"--junitxml={junit_path}",
    ]
    if keyword:
        cmd.extend(["-k", keyword])

    proc = subprocess.run(cmd, cwd=str(ROOT), capture_output=True, text=True)
    finished = datetime.now(timezone.utc)
    duration = (finished - started).total_seconds()

    tests = parse_junit(junit_path) if junit_path.exists() else parse_stdout(proc.stdout)
    summary = summarize(tests)
    if proc.returncode != 0 and summary["failed"] == 0 and summary["errors"] == 0:
        # collection error 等
        summary["errors"] = max(summary["errors"], 1)
        if not tests:
            tests.append(
                {
                    "nodeid": "(collection)",
                    "classname": "",
                    "name": "collection",
                    "outcome": "error",
                    "duration": 0,
                    "message": (proc.stderr or proc.stdout)[-2000:],
                }
            )

    status = "passed" if proc.returncode == 0 else "failed"
    report = {
        "id": run_id,
        "status": status,
        "exit_code": proc.returncode,
        "summary": summary,
        "tests": tests,
        "started_at": started.isoformat(),
        "finished_at": finished.isoformat(),
        "duration_sec": round(duration, 3),
        "command": cmd,
        "stdout_tail": (proc.stdout or "")[-4000:],
        "stderr_tail": (proc.stderr or "")[-2000:],
        "junit": str(junit_path) if junit_path.exists() else None,
    }
    report_path.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    latest = RESULTS_DIR / "latest.json"
    latest.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    return report


def parse_junit(path: Path) -> list[dict]:
    import xml.etree.ElementTree as ET

    root = ET.parse(path).getroot()
    tests: list[dict] = []
    suites = root.findall("testsuite")
    if root.tag == "testsuite":
        suites = [root]
    for suite in suites:
        for case in suite.findall("testcase"):
            classname = case.get("classname", "")
            name = case.get("name", "")
            duration = float(case.get("time") or 0)
            nodeid = f"{classname}::{name}" if classname else name
            outcome = "passed"
            message = ""
            if case.find("failure") is not None:
                outcome = "failed"
                el = case.find("failure")
                message = (el.get("message") or "") + "\n" + (el.text or "")
            elif case.find("error") is not None:
                outcome = "error"
                el = case.find("error")
                message = (el.get("message") or "") + "\n" + (el.text or "")
            elif case.find("skipped") is not None:
                outcome = "skipped"
                el = case.find("skipped")
                message = el.get("message") or (el.text or "")
            tests.append(
                {
                    "nodeid": nodeid,
                    "classname": classname,
                    "name": name,
                    "outcome": outcome,
                    "duration": round(duration, 4),
                    "message": message.strip()[:2000],
                }
            )
    return tests


def parse_stdout(stdout: str) -> list[dict]:
    """junit が無い場合の簡易フォールバック"""
    tests: list[dict] = []
    for line in stdout.splitlines():
        m = re.match(r"^(tests/[^\s]+)\s+(PASSED|FAILED|SKIPPED|ERROR)", line)
        if not m:
            continue
        nodeid, outcome = m.group(1), m.group(2).lower()
        if outcome == "error":
            outcome = "error"
        tests.append(
            {
                "nodeid": nodeid,
                "classname": nodeid.rsplit("::", 1)[0] if "::" in nodeid else "",
                "name": nodeid.rsplit("::", 1)[-1],
                "outcome": outcome if outcome != "error" else "error",
                "duration": 0,
                "message": "",
            }
        )
    return tests


def summarize(tests: list[dict]) -> dict:
    summary = {"passed": 0, "failed": 0, "skipped": 0, "errors": 0, "total": len(tests)}
    for t in tests:
        o = t.get("outcome", "")
        if o == "passed":
            summary["passed"] += 1
        elif o == "failed":
            summary["failed"] += 1
        elif o == "skipped":
            summary["skipped"] += 1
        elif o == "error":
            summary["errors"] += 1
    return summary


def list_reports(limit: int = 20) -> list[dict]:
    if not RESULTS_DIR.exists():
        return []
    files = sorted(
        [p for p in RESULTS_DIR.glob("*.json") if p.name != "latest.json"],
        key=lambda p: p.stat().st_mtime,
        reverse=True,
    )
    rows = []
    for p in files[:limit]:
        try:
            data = json.loads(p.read_text(encoding="utf-8"))
            rows.append(
                {
                    "id": data.get("id", p.stem),
                    "status": data.get("status"),
                    "summary": data.get("summary"),
                    "started_at": data.get("started_at"),
                    "finished_at": data.get("finished_at"),
                    "duration_sec": data.get("duration_sec"),
                    "path": str(p),
                }
            )
        except (json.JSONDecodeError, OSError):
            continue
    return rows


def load_report(run_id: str) -> dict | None:
    if run_id == "latest":
        path = RESULTS_DIR / "latest.json"
    else:
        path = RESULTS_DIR / f"{run_id}.json"
    if not path.exists():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def main() -> int:
    parser = argparse.ArgumentParser(description="ユニットテスト実行・結果保存")
    sub = parser.add_subparsers(dest="action", required=True)

    p_run = sub.add_parser("run", help="テスト実行")
    p_run.add_argument("--path", default="tests")
    p_run.add_argument("-k", "--keyword", help="pytest -k フィルタ")
    p_run.add_argument("--json", action="store_true")

    p_list = sub.add_parser("list", help="過去の実行一覧")
    p_list.add_argument("--limit", type=int, default=20)
    p_list.add_argument("--json", action="store_true")

    p_show = sub.add_parser("show", help="実行結果の詳細")
    p_show.add_argument("run_id", nargs="?", default="latest")
    p_show.add_argument("--json", action="store_true")

    args = parser.parse_args()

    if args.action == "run":
        report = run_tests(path=args.path, keyword=args.keyword)
        if args.json:
            print(json.dumps(report, indent=2, ensure_ascii=False))
        else:
            s = report["summary"]
            print(f"Run: {report['id']}")
            print(f"Status: {report['status']}")
            print(
                f"Passed={s['passed']} Failed={s['failed']} "
                f"Skipped={s['skipped']} Errors={s['errors']} "
                f"({report['duration_sec']}s)"
            )
            print(f"Report: {RESULTS_DIR / (report['id'] + '.json')}")
            if report.get("error"):
                print(f"Error: {report['error']}")
        return 0 if report["status"] == "passed" else 1

    if args.action == "list":
        rows = list_reports(args.limit)
        if args.json:
            print(json.dumps({"runs": rows}, indent=2, ensure_ascii=False))
        else:
            if not rows:
                print("実行結果がありません")
                return 0
            print(f"{'ID':<28} {'Status':<8} {'Pass':>4} {'Fail':>4} {'Dur':>7}")
            print("-" * 60)
            for r in rows:
                s = r.get("summary") or {}
                print(
                    f"{r['id']:<28} {r.get('status', '?'):<8} "
                    f"{s.get('passed', 0):>4} {s.get('failed', 0):>4} "
                    f"{r.get('duration_sec', 0):>7}"
                )
        return 0

    if args.action == "show":
        report = load_report(args.run_id)
        if not report:
            print(f"見つかりません: {args.run_id}", file=sys.stderr)
            return 1
        if args.json:
            print(json.dumps(report, indent=2, ensure_ascii=False))
        else:
            print(json.dumps(report, indent=2, ensure_ascii=False))
        return 0

    return 1


if __name__ == "__main__":
    sys.exit(main())
