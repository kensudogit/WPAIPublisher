#!/usr/bin/env python3
"""
WPAIPublisher メインオーケストレーター

使用例:
  python wpaipublish.py intake validate
  python wpaipublish.py convert prepare
  python wpaipublish.py validate run <session_id>
  python wpaipublish.py quality run <session_id>
  python wpaipublish.py visual run <session_id>
  python wpaipublish.py git pr <session_id>
  python wpaipublish.py knowledge index
  python wpaipublish.py knowledge retrieve --session <session_id>
  python wpaipublish.py ai route --stage wp_conversion --session <session_id>
  python wpaipublish.py agent run <session_id>
  python wpaipublish.py deploy staging <session_id>
  python wpaipublish.py deploy production <session_id> --confirm
  python wpaipublish.py rollback <session_id> production --confirm
  python wpaipublish.py status
"""

import argparse
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
SCRIPTS = ROOT / "scripts"


def run_script(cmd: list[str]) -> int:
    result = subprocess.run(cmd, cwd=str(ROOT))
    return result.returncode


def cmd_intake(args: argparse.Namespace) -> int:
    if args.action == "validate":
        cmd = [sys.executable, str(SCRIPTS / "intake" / "validate_intake.py")]
        if args.path:
            cmd.append(args.path)
        return run_script(cmd)
    print(f"不明な intake アクション: {args.action}", file=sys.stderr)
    return 1


def cmd_convert(args: argparse.Namespace) -> int:
    if args.action == "prepare":
        cmd = [sys.executable, str(SCRIPTS / "convert" / "prepare_claude_input.py")]
        if args.target:
            cmd.append(args.target)
        if args.session_id:
            cmd.extend(["--session-id", args.session_id])
        return run_script(cmd)
    if args.action == "mark-done":
        session_id = args.target
        if not session_id:
            print("ERROR: セッションIDを指定してください", file=sys.stderr)
            return 1
        cmd = [sys.executable, str(SCRIPTS / "convert" / "mark_converted.py"), session_id]
        if args.notes:
            cmd.extend(["--notes", args.notes])
        return run_script(cmd)
    print(f"不明な convert アクション: {args.action}", file=sys.stderr)
    return 1


def cmd_validate(args: argparse.Namespace) -> int:
    cmd = [sys.executable, str(SCRIPTS / "validate" / "run_validation.py"), args.session_id]
    if args.json:
        cmd.append("--json")
    return run_script(cmd)


def cmd_quality(args: argparse.Namespace) -> int:
    cmd = [sys.executable, str(SCRIPTS / "quality" / "run_gates.py"), args.session_id]
    if args.stage:
        cmd.extend(["--stage", args.stage])
    if args.json:
        cmd.append("--json")
    return run_script(cmd)


def cmd_visual(args: argparse.Namespace) -> int:
    cmd = [sys.executable, str(SCRIPTS / "visual" / "run_regression.py"), args.session_id]
    if args.env:
        cmd.extend(["--env", args.env])
    if args.update:
        cmd.append("--update")
    if args.json:
        cmd.append("--json")
    return run_script(cmd)


def cmd_git(args: argparse.Namespace) -> int:
    if args.action == "pr":
        cmd = [sys.executable, str(SCRIPTS / "git" / "create_pr.py"), args.session_id]
        if args.base:
            cmd.extend(["--base", args.base])
        return run_script(cmd)
    if args.action == "deploy":
        bash_cmd = ["bash", str(SCRIPTS / "git" / "deploy_via_git.sh"), args.env, args.session_id]
        if args.confirm:
            bash_cmd.append("--confirm")
        return run_script(bash_cmd)
    if args.action == "rollback":
        bash_cmd = ["bash", str(SCRIPTS / "git" / "rollback_git.sh"), args.session_id, args.env]
        if args.confirm:
            bash_cmd.append("--confirm")
        return run_script(bash_cmd)
    return 1


def cmd_knowledge(args: argparse.Namespace) -> int:
    if args.action == "index":
        cmd = [sys.executable, str(SCRIPTS / "knowledge" / "index.py")]
        if args.session:
            cmd.extend(["--session", args.session])
        if args.rebuild:
            cmd.append("--rebuild")
        return run_script(cmd)
    if args.action == "retrieve":
        cmd = [sys.executable, str(SCRIPTS / "knowledge" / "retrieve.py"),
               "--session", args.session, "--top-k", str(args.top_k)]
        return run_script(cmd)
    return 1


def cmd_ai(args: argparse.Namespace) -> int:
    if args.action == "list":
        return run_script([sys.executable, str(SCRIPTS / "ai" / "router.py"), "--list",
                           "--stage", "wp_conversion", "--session", "none"])
    cmd = [sys.executable, str(SCRIPTS / "ai" / "router.py"),
           "--stage", args.stage, "--session", args.session]
    if args.prompt:
        cmd.extend(["--prompt", args.prompt])
    if args.auto_cli:
        cmd.append("--auto-cli")
    return run_script(cmd)


def cmd_agent(args: argparse.Namespace) -> int:
    cmd = [sys.executable, str(SCRIPTS / "agent" / "orchestrator.py"), args.session_id]
    if args.action == "resume":
        cmd.append("--resume")
    if args.approve:
        cmd.append("--approve")
    if args.from_stage:
        cmd.extend(["--from-stage", args.from_stage])
    if args.dry_run:
        cmd.append("--dry-run")
    return run_script(cmd)


def cmd_deploy(args: argparse.Namespace) -> int:
    if args.via_git:
        bash_cmd = ["bash", str(SCRIPTS / "git" / "deploy_via_git.sh"), args.env, args.session_id]
        if args.confirm:
            bash_cmd.append("--confirm")
        return run_script(bash_cmd)
    if args.env == "staging":
        return run_script(["bash", str(SCRIPTS / "deploy" / "deploy_staging.sh"), args.session_id])
    cmd = ["bash", str(SCRIPTS / "deploy" / "deploy_production.sh"), args.session_id]
    if args.confirm:
        cmd.append("--confirm")
    return run_script(cmd)


def cmd_rollback(args: argparse.Namespace) -> int:
    if args.via_git:
        bash_cmd = ["bash", str(SCRIPTS / "git" / "rollback_git.sh"), args.session_id, args.env]
        if args.confirm:
            bash_cmd.append("--confirm")
        return run_script(bash_cmd)
    cmd = ["bash", str(SCRIPTS / "rollback" / "rollback.sh"), args.session_id, args.env]
    if args.confirm:
        cmd.append("--confirm")
    return run_script(cmd)


def cmd_status(_args: argparse.Namespace) -> int:
    output_dir = ROOT / "output"
    if not output_dir.exists():
        print("セッションなし")
        return 0

    sessions = sorted(output_dir.iterdir(), key=lambda p: p.stat().st_mtime, reverse=True)
    if not sessions:
        print("セッションなし")
        return 0

    print(f"{'Session ID':<20} {'Status':<22} {'Agent':<12} {'Target':<12}")
    print("-" * 68)
    for s in sessions:
        if not s.is_dir():
            continue
        task_file = s / "task.json"
        agent_file = s / "agent_state.json"
        if task_file.exists():
            task = json.loads(task_file.read_text(encoding="utf-8"))
            status = task.get("status", "unknown")
            target = task.get("manifest", {}).get("target", {}).get("type", "?")
        else:
            status, target = "no task", "?"
        agent_status = "—"
        if agent_file.exists():
            agent_status = json.loads(agent_file.read_text(encoding="utf-8")).get("status", "?")
        print(f"{s.name:<20} {status:<22} {agent_status:<12} {target:<12}")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(
        description="WPAIPublisher - AI出力をWordPressへ反映するワークフロー",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    sub = parser.add_subparsers(dest="command")

    p_intake = sub.add_parser("intake", help="AI出力の受け取り")
    p_intake.add_argument("action", choices=["validate"])
    p_intake.add_argument("path", nargs="?", help="intakeディレクトリ")

    p_convert = sub.add_parser("convert", help="AI変換")
    p_convert.add_argument("action", choices=["prepare", "mark-done"])
    p_convert.add_argument("target", nargs="?", help="intakeディレクトリまたはセッションID")
    p_convert.add_argument("--session-id", help="セッションID指定（prepare時）")
    p_convert.add_argument("--notes", help="変換メモ")

    p_validate = sub.add_parser("validate", help="基本検証（PHP構文等）")
    p_validate.add_argument("action", choices=["run"])
    p_validate.add_argument("session_id")
    p_validate.add_argument("--json", action="store_true")

    p_quality = sub.add_parser("quality", help="品質ゲート（HTML/SEO/a11y/security/perf）")
    p_quality.add_argument("action", choices=["run"])
    p_quality.add_argument("session_id")
    p_quality.add_argument("--stage", default="pr_merge")
    p_quality.add_argument("--json", action="store_true")

    p_visual = sub.add_parser("visual", help="ビジュアル回帰テスト")
    p_visual.add_argument("action", choices=["run"])
    p_visual.add_argument("session_id")
    p_visual.add_argument("--env", default="staging")
    p_visual.add_argument("--update", action="store_true", help="ベースライン更新")
    p_visual.add_argument("--json", action="store_true")

    p_git = sub.add_parser("git", help="Git CI/CD")
    p_git.add_argument("action", choices=["pr", "deploy", "rollback"])
    p_git.add_argument("session_id", nargs="?")
    p_git.add_argument("--env", default="staging", choices=["staging", "production"])
    p_git.add_argument("--base", default="staging")
    p_git.add_argument("--confirm", action="store_true")

    p_knowledge = sub.add_parser("knowledge", help="RAGナレッジベース")
    p_knowledge.add_argument("action", choices=["index", "retrieve"])
    p_knowledge.add_argument("--session", help="セッションID")
    p_knowledge.add_argument("--rebuild", action="store_true")
    p_knowledge.add_argument("--top-k", type=int, default=5)

    p_ai = sub.add_parser("ai", help="マルチAIルーター")
    p_ai.add_argument("action", choices=["route", "list"])
    p_ai.add_argument("--stage", default="wp_conversion")
    p_ai.add_argument("--session", default="")
    p_ai.add_argument("--prompt", default="prompts/convert-to-wp.md")
    p_ai.add_argument("--auto-cli", action="store_true")

    p_agent = sub.add_parser("agent", help="AIエージェント自律実行")
    p_agent.add_argument("action", choices=["run", "resume"])
    p_agent.add_argument("session_id")
    p_agent.add_argument("--approve", action="store_true")
    p_agent.add_argument("--from-stage", help="指定ステージから開始")
    p_agent.add_argument("--dry-run", action="store_true")

    p_deploy = sub.add_parser("deploy", help="デプロイ")
    p_deploy.add_argument("env", choices=["staging", "production"])
    p_deploy.add_argument("session_id")
    p_deploy.add_argument("--confirm", action="store_true")
    p_deploy.add_argument("--via-git", action="store_true", help="Gitベースデプロイ")

    p_rollback = sub.add_parser("rollback", help="ロールバック")
    p_rollback.add_argument("session_id")
    p_rollback.add_argument("env", choices=["staging", "production"], default="production", nargs="?")
    p_rollback.add_argument("--confirm", action="store_true")
    p_rollback.add_argument("--via-git", action="store_true")

    sub.add_parser("status", help="セッション一覧")

    args = parser.parse_args()
    if not args.command:
        parser.print_help()
        return 0

    handlers = {
        "intake": cmd_intake,
        "convert": cmd_convert,
        "validate": cmd_validate,
        "quality": cmd_quality,
        "visual": cmd_visual,
        "git": cmd_git,
        "knowledge": cmd_knowledge,
        "ai": cmd_ai,
        "agent": cmd_agent,
        "deploy": cmd_deploy,
        "rollback": cmd_rollback,
        "status": cmd_status,
    }
    return handlers[args.command](args)


if __name__ == "__main__":
    sys.exit(main())
