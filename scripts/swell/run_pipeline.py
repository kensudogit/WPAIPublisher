#!/usr/bin/env python3
"""SWELL 一連パイプライン:
analyze → convert → validate → deploy → visual → git → report
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def run(cmd: list[str], *, quiet: bool = False) -> tuple[int, str]:
    if not quiet:
        print("+", " ".join(cmd))
    result = subprocess.run(
        cmd,
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    out = (result.stdout or "") + (result.stderr or "")
    if not quiet and out.strip():
        print(out.strip())
    return result.returncode, out


def main() -> int:
    parser = argparse.ArgumentParser(description="SWELL 一連パイプライン")
    parser.add_argument("session_id", nargs="?", help="既存セッションID")
    parser.add_argument("--source-dir", help="HTML フォルダ（未作成セッション向け）")
    parser.add_argument("--select", action="append", help="HTML 相対パス（複数可）")
    parser.add_argument("--theme-slug", default="swell-child")
    parser.add_argument("--parent-theme", default="swell")
    parser.add_argument("--skip-git", action="store_true")
    parser.add_argument("--skip-deploy", action="store_true")
    parser.add_argument("--skip-visual", action="store_true")
    parser.add_argument("--push", action="store_true", help="git push まで実行")
    parser.add_argument("--pr", action="store_true", help="PR 作成")
    parser.add_argument("--visual-update", action="store_true", help="初回ベースライン更新")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    session_id = args.session_id
    steps: list[dict] = []

    # 0. 必要なら intake pipeline でセッション作成
    if args.source_dir:
        if not args.select:
            print("ERROR: --source-dir 利用時は --select が必要です", file=sys.stderr)
            return 1
        session_id = session_id or datetime.now().strftime("swell-%Y%m%d-%H%M%S")
        cmd = [
            sys.executable,
            str(ROOT / "wpaipublish.py"),
            "intake",
            "pipeline",
            args.source_dir,
            "--session-id",
            session_id,
            "--target-type",
            "page",
            "--theme-slug",
            args.theme_slug,
        ]
        for sel in args.select:
            cmd.extend(["--select", sel])
        rc, out = run(cmd)
        steps.append({"step": "intake_pipeline", "ok": rc == 0})
        if rc != 0:
            return _fail(steps, session_id, args.json, out)

    if not session_id:
        print("ERROR: session_id または --source-dir が必要です", file=sys.stderr)
        return 1

    py = sys.executable

    # 1. HTML 解析
    rc, out = run([py, str(ROOT / "scripts" / "analyze" / "html_structure.py"), session_id])
    steps.append({"step": "analyze", "ok": rc == 0})
    if rc != 0:
        return _fail(steps, session_id, args.json, out)

    # 2. SWELL 変換
    rc, out = run(
        [
            py,
            str(ROOT / "scripts" / "swell" / "convert_to_swell.py"),
            session_id,
            "--theme-slug",
            args.theme_slug,
            "--parent-theme",
            args.parent_theme,
        ]
    )
    steps.append({"step": "swell_convert", "ok": rc == 0})
    if rc != 0:
        return _fail(steps, session_id, args.json, out)

    # 3. validate（失敗してもレポートまで進める。deploy は valid 必須）
    rc, out = run([py, str(ROOT / "wpaipublish.py"), "validate", "run", session_id])
    steps.append({"step": "validate", "ok": rc == 0})
    validation_errors: list[str] = []
    validation_path = ROOT / "output" / session_id / "validation.json"
    if validation_path.exists():
        try:
            vdata = json.loads(validation_path.read_text(encoding="utf-8"))
            validation_errors = list(vdata.get("errors") or [])
        except Exception:  # noqa: BLE001
            pass

    # 4. deploy staging（失敗しても後続へ。Railway では WP 実体が無くてもスナップショット可）
    if not args.skip_deploy:
        rc, out = run([py, str(ROOT / "wpaipublish.py"), "deploy", "staging", session_id])
        steps.append({"step": "deploy_staging", "ok": rc == 0, "detail": out[-800:] if rc != 0 else ""})

    # 5. visual
    if not args.skip_visual:
        vcmd = [py, str(ROOT / "wpaipublish.py"), "visual", "run", session_id]
        if args.visual_update:
            vcmd.append("--update")
        rc, out = run(vcmd)
        steps.append({"step": "visual", "ok": rc == 0, "detail": out[-800:] if rc != 0 else ""})

    # 6. git
    if not args.skip_git:
        gcmd = [
            py,
            str(ROOT / "scripts" / "git" / "commit_push.py"),
            session_id,
        ]
        if not args.push:
            gcmd.append("--no-push")
        if args.pr:
            gcmd.append("--pr")
        rc, out = run(gcmd)
        steps.append({"step": "git", "ok": rc == 0})

    # 7. report
    rc, out = run([py, str(ROOT / "scripts" / "report" / "generate_report.py"), session_id])
    steps.append({"step": "report", "ok": rc == 0})

    core_ok = all(s["ok"] for s in steps if s["step"] in {"analyze", "swell_convert", "report"})
    result = {
        "session_id": session_id,
        "steps": steps,
        "ok": core_ok,
        "report": str(ROOT / "output" / session_id / "change_report.md"),
        "validation_errors": validation_errors,
    }
    if not core_ok and not result.get("error"):
        failed = [s["step"] for s in steps if not s["ok"] and s["step"] in {"analyze", "swell_convert", "report"}]
        result["error"] = f"必須ステップ失敗: {', '.join(failed)}"
    elif validation_errors and not any(s["step"] == "deploy_staging" and s["ok"] for s in steps):
        # 検証 NG で deploy できなかった場合は UI 向けに明示（全体 ok はコア成功なら true）
        result["warning"] = "検証エラーのためデプロイをスキップ/失敗: " + "; ".join(validation_errors[:5])

    if args.json:
        print(json.dumps(result, ensure_ascii=False))
    else:
        print("\nSWELL pipeline finished")
        print(f"  session: {session_id}")
        for s in steps:
            print(f"  [{'OK' if s['ok'] else 'NG'}] {s['step']}")
        print(f"  report: {result['report']}")
    return 0 if result["ok"] else 1


def _fail(steps: list, session_id: str | None, as_json: bool, out: str) -> int:
    result = {"session_id": session_id, "steps": steps, "ok": False, "error": out[-1500:]}
    if as_json:
        print(json.dumps(result, ensure_ascii=False))
    else:
        print("PIPELINE FAILED", file=sys.stderr)
        for s in steps:
            print(f"  [{'OK' if s['ok'] else 'NG'}] {s['step']}", file=sys.stderr)
    return 1


if __name__ == "__main__":
    sys.exit(main())
