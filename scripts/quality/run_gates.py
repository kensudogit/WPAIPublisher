#!/usr/bin/env python3
"""品質ゲート統合実行"""

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))

from lib.config import get_session_dir, load_quality_gates  # noqa: E402
from quality.gates.html_gate import check_html  # noqa: E402
from quality.gates.seo_gate import check_seo  # noqa: E402
from quality.gates.a11y_gate import check_accessibility  # noqa: E402
from quality.gates.security_gate import check_security  # noqa: E402
from quality.gates.performance_gate import check_performance  # noqa: E402

GATE_RUNNERS = {
    "html": check_html,
    "seo": check_seo,
    "accessibility": check_accessibility,
    "security": check_security,
    "performance": check_performance,
}


def run_gates(session_id: str, stage: str | None = None) -> dict:
    config = load_quality_gates()
    session_dir = get_session_dir(session_id)
    wp_dir = session_dir / "wordpress"

    if not wp_dir.exists():
        return {"passed": False, "error": f"wordpress/ が見つかりません: {wp_dir}"}

    gates_config = config.get("gates", {})
    required = set(config.get("required_for", {}).get(stage or "pr_merge", []))

    results = []
    blocking_failures = []
    warnings = []

    for gate_name, runner in GATE_RUNNERS.items():
        gate_cfg = gates_config.get(gate_name, {})
        if not gate_cfg.get("enabled", True):
            continue

        result = runner(wp_dir, gate_cfg.get("rules", {}))
        result.blocking = gate_cfg.get("blocking", result.blocking)
        results.append(result)

        is_required = gate_name in required or not stage
        if not result.passed:
            if result.blocking and is_required:
                blocking_failures.extend(result.errors)
            else:
                warnings.extend(result.warnings + result.errors)

    # visual_regression は別スクリプトで実行、結果を読み込み
    vr_result_path = session_dir / "visual_regression.json"
    if vr_result_path.exists():
        vr = json.loads(vr_result_path.read_text(encoding="utf-8"))
        if not vr.get("passed") and "visual_regression" in required:
            blocking_failures.append("ビジュアル回帰テスト失敗")

    passed = len(blocking_failures) == 0
    report = {
        "session_id": session_id,
        "stage": stage,
        "passed": passed,
        "blocking_failures": blocking_failures,
        "warnings": warnings,
        "gates": [
            {
                "gate": r.gate,
                "passed": r.passed,
                "blocking": r.blocking,
                "errors": r.errors,
                "warnings": r.warnings,
                "metrics": r.metrics,
            }
            for r in results
        ],
    }

    report_path = session_dir / "quality_gates.json"
    report_path.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description="品質ゲート実行")
    parser.add_argument("session_id", help="セッションID")
    parser.add_argument("--stage", default="pr_merge", help="必須ゲートステージ")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    report = run_gates(args.session_id, args.stage)

    if args.json:
        print(json.dumps(report, indent=2, ensure_ascii=False))
    else:
        status = "PASSED" if report["passed"] else "FAILED"
        print(f"QUALITY GATES {status}: {args.session_id}")
        for gate in report.get("gates", []):
            icon = "OK" if gate["passed"] else "NG"
            print(f"  [{icon}] {gate['gate']}")
            for e in gate.get("errors", []):
                print(f"      ERROR: {e}")
            for w in gate.get("warnings", []):
                print(f"      WARN: {w}")

    return 0 if report.get("passed") else 1


if __name__ == "__main__":
    sys.exit(main())
