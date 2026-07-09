#!/usr/bin/env python3
"""AIエージェント自律実行オーケストレーター

要件整理からデプロイまでのパイプラインを自動実行する。
手動介入が必要なステージ（AI変換等）では一時停止し、再開を待つ。
"""

import argparse
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))

import yaml  # noqa: E402

from lib.config import get_output_dir, get_session_dir  # noqa: E402


class AgentOrchestrator:
    def __init__(self, session_id: str, pipeline_path: Path | None = None):
        self.session_id = session_id
        self.session_dir = get_session_dir(session_id)
        self.pipeline_path = pipeline_path or ROOT / "workflow" / "pipeline.yaml"
        self.state_file = self.session_dir / "agent_state.json"
        self.pipeline = self._load_pipeline()
        self.state = self._load_state()

    def _load_pipeline(self) -> dict:
        with open(self.pipeline_path, encoding="utf-8") as f:
            return yaml.safe_load(f)

    def _load_state(self) -> dict:
        if self.state_file.exists():
            return json.loads(self.state_file.read_text(encoding="utf-8"))
        return {"session_id": self.session_id, "completed_stages": [], "status": "running"}

    def _save_state(self) -> None:
        self.session_dir.mkdir(parents=True, exist_ok=True)
        self.state_file.write_text(json.dumps(self.state, indent=2, ensure_ascii=False), encoding="utf-8")

    def _run_script(self, script: str, args: list[str] | None = None) -> tuple[int, str]:
        script_path = ROOT / script
        if script.endswith(".sh"):
            cmd = ["bash", str(script_path)] + (args or [])
        else:
            cmd = [sys.executable, str(script_path)] + (args or [])

        # プレースホルダー置換
        cmd = [a.replace("{session_id}", self.session_id) for a in cmd]
        result = subprocess.run(cmd, cwd=str(ROOT), capture_output=True, text=True)
        output = (result.stdout + result.stderr).strip()
        return result.returncode, output

    def _format_args(self, args: list[str] | None) -> list[str]:
        if not args:
            return [self.session_id]
        return [a.replace("{session_id}", self.session_id) for a in args]

    def run_stage(self, stage: dict) -> dict[str, Any]:
        stage_id = stage["id"]
        print(f"\n[agent] Stage: {stage_id} - {stage.get('name', '')}")

        if stage_id in self.state.get("completed_stages", []):
            print(f"[agent] Skipped (already completed): {stage_id}")
            return {"stage": stage_id, "status": "skipped"}

        # AIプロバイダーステージ
        if stage.get("ai_provider"):
            from ai.router import execute_stage  # noqa: E402
            prompt_path = ROOT / stage.get("prompt", "prompts/convert-to-wp.md")
            result = execute_stage(stage_id, prompt_path, self.session_id)
            if result.requires_manual:
                self.state["status"] = "waiting_manual"
                self.state["waiting_stage"] = stage_id
                self.state["waiting_since"] = datetime.now(timezone.utc).isoformat()
                self._save_state()
                print(f"[agent] PAUSED: 手動実行が必要です")
                if result.instructions_path:
                    print(f"[agent] → {result.instructions_path}")
                return {"stage": stage_id, "status": "waiting_manual", "instructions": str(result.instructions_path)}

        # スクリプト実行
        if stage.get("script"):
            args = self._format_args(stage.get("args"))
            if stage["script"].endswith(".sh") and not args:
                args = [self.session_id]
            rc, output = self._run_script(stage["script"], args)
            print(output)
            if rc != 0:
                self.state["status"] = "failed"
                self.state["failed_stage"] = stage_id
                self.state["error"] = output[-500:]
                self._save_state()
                return {"stage": stage_id, "status": "failed", "error": output}

        # 承認が必要なステージ
        if stage.get("requires_approval"):
            self.state["status"] = "waiting_approval"
            self.state["waiting_stage"] = stage_id
            self._save_state()
            print(f"[agent] PAUSED: 承認が必要です (--resume --approve で続行)")
            return {"stage": stage_id, "status": "waiting_approval"}

        self.state.setdefault("completed_stages", []).append(stage_id)
        self._save_state()
        return {"stage": stage_id, "status": "completed"}

    def run(self, from_stage: str | None = None, approve: bool = False) -> dict:
        stages = self.pipeline.get("stages", [])
        start_idx = 0
        if from_stage:
            for i, s in enumerate(stages):
                if s["id"] == from_stage:
                    start_idx = i
                    break

        if approve and self.state.get("status") == "waiting_approval":
            waiting = self.state.get("waiting_stage")
            for i, s in enumerate(stages):
                if s["id"] == waiting:
                    start_idx = i
                    self.state["status"] = "running"
                    break

        results = []
        for stage in stages[start_idx:]:
            result = self.run_stage(stage)
            results.append(result)
            if result["status"] in ("waiting_manual", "waiting_approval", "failed"):
                break

        if all(r["status"] in ("completed", "skipped") for r in results):
            self.state["status"] = "completed"
            self._save_state()

        return {"session_id": self.session_id, "status": self.state["status"], "results": results}

    def resume(self, approve: bool = False) -> dict:
        waiting = self.state.get("waiting_stage")
        if self.state.get("status") == "waiting_manual" and waiting:
            self.state["status"] = "running"
            if waiting not in self.state.get("completed_stages", []):
                self.state["completed_stages"].append(waiting)
            self._save_state()
            return self.run(from_stage=waiting)
        return self.run(approve=approve)


def main() -> int:
    parser = argparse.ArgumentParser(description="AIエージェント自律実行")
    parser.add_argument("session_id", help="セッションID")
    parser.add_argument("--resume", action="store_true", help="中断から再開")
    parser.add_argument("--approve", action="store_true", help="承認待ちステージを承認して続行")
    parser.add_argument("--from-stage", help="指定ステージから開始")
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--dry-run", action="store_true", help="ステージ一覧を表示")
    args = parser.parse_args()

    orchestrator = AgentOrchestrator(args.session_id)

    if args.dry_run:
        print(f"Pipeline for session: {args.session_id}")
        for s in orchestrator.pipeline.get("stages", []):
            auto = "auto" if s.get("auto") else "manual"
            print(f"  [{auto}] {s['id']}: {s.get('name', '')}")
        return 0

    if args.resume:
        report = orchestrator.resume(approve=args.approve)
    else:
        report = orchestrator.run(from_stage=args.from_stage, approve=args.approve)

    if args.json:
        print(json.dumps(report, indent=2, ensure_ascii=False))
    else:
        print(f"\n[agent] Status: {report['status']}")
        for r in report.get("results", []):
            print(f"  {r['stage']}: {r['status']}")

    return 0 if report["status"] in ("completed", "waiting_manual", "waiting_approval") else 1


if __name__ == "__main__":
    sys.exit(main())
