#!/usr/bin/env python3
"""
WPAIPublisher メインオーケストレーター（CLI エントリポイント）

本ファイルはビジネスロジックをほぼ持たず、サブコマンドを受けて
`scripts/` 配下の専用スクリプトへ処理を委譲する薄いラッパーです。

【全体の流れ（典型）】
  1. intake   … AI 出力 HTML を受け取り・選択・パッケージ化
  2. convert / swell / ai / agent
              … WordPress / SWELL 向け変換（自動 or Claude Code）
  3. validate / quality / visual
              … 検証・品質ゲート・見た目差分
  4. deploy / git / report
              … ステージング反映・Git・変更レポート

【成果物の置き場】
  セッション単位で `output/<session_id>/` に集約される。

使用例:
  python wpaipublish.py intake list <folder>
  python wpaipublish.py intake select <folder> --interactive
  python wpaipublish.py intake pipeline <folder> --select a.html --select b.html
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
  python wpaipublish.py test run
  python wpaipublish.py test list
  python wpaipublish.py analyze <session_id>
  python wpaipublish.py swell convert <session_id>
  python wpaipublish.py swell pipeline --source-dir <folder> --select a.html
  python wpaipublish.py git commit <session_id> --push
  python wpaipublish.py report generate <session_id>
  python wpaipublish.py status
"""

import argparse
import json
import subprocess
import sys
from pathlib import Path

# リポジトリルート（本ファイルの親ディレクトリ）
ROOT = Path(__file__).resolve().parent
# 実処理スクリプト群のルート（委譲先）
SCRIPTS = ROOT / "scripts"


def run_script(cmd: list[str]) -> int:
    """サブプロセスでスクリプトを実行し、終了コードを返す。

    cwd は常にリポジトリルートにする。相対パスや設定ファイル解決を
    各スクリプト側で安定させるため。
    """
    result = subprocess.run(cmd, cwd=str(ROOT))
    return result.returncode


# ---------------------------------------------------------------------------
# intake … AI 出力の受け取り・HTML 選択・パイプライン投入
# ---------------------------------------------------------------------------

def cmd_intake(args: argparse.Namespace) -> int:
    """intake サブコマンドの振り分け。

    validate  : manifest.json とファイル構成の妥当性チェック
    list      : フォルダ内 HTML 一覧（関連 CSS/JS 付き）
    select    : 選択 HTML から intake パッケージを作成
    pipeline  : 選択 → validate → convert prepare まで一括
    """
    # --- validate: intake パッケージの検証 ---
    if args.action == "validate":
        # 現在の Python インタプリタで validate_intake.py を起動
        cmd = [sys.executable, str(SCRIPTS / "intake" / "validate_intake.py")]
        # path 省略時はスクリプト側が incoming 最新などを解決する
        if args.path:
            cmd.append(args.path)
        return run_script(cmd)

    # --- list: HTML ファイル一覧（Web UI / CLI 共通） ---
    if args.action == "list":
        if not args.path:
            print("ERROR: HTML フォルダを指定してください", file=sys.stderr)
            return 1
        cmd = [sys.executable, str(SCRIPTS / "intake" / "select_files.py"), "list", args.path]
        if args.json:
            cmd.append("--json")
        return run_script(cmd)

    # --- select: 対話 or --select 指定でパッケージ作成 ---
    if args.action == "select":
        if not args.path:
            print("ERROR: HTML フォルダを指定してください", file=sys.stderr)
            return 1
        # 対話モード: ターミナル上で番号選択
        if args.interactive:
            cmd = [
                sys.executable,
                str(SCRIPTS / "intake" / "select_files.py"),
                "interactive",
                args.path,
                "--target-type",
                args.target_type,
                "--theme-slug",
                args.theme_slug,
                "--tool",
                args.tool,
            ]
            return run_script(cmd)
        # 非対話: --select が1つ以上必須（action=append でリスト化済み）
        if not args.select:
            print("ERROR: --select または --interactive を指定してください", file=sys.stderr)
            return 1
        cmd = [
            sys.executable,
            str(SCRIPTS / "intake" / "select_files.py"),
            "create",
            args.path,
            "--target-type",
            args.target_type,
            "--theme-slug",
            args.theme_slug,
            "--tool",
            args.tool,
        ]
        # argparse の append 結果を、サブプロセス向けに --select 値 のペアへ展開
        # 例: ["a.html","b.html"] → ["--select","a.html","--select","b.html"]
        for sel in args.select:
            cmd.extend(["--select", sel])
        if args.package_name:
            cmd.extend(["--package-name", args.package_name])
        if args.notes:
            cmd.extend(["--notes", args.notes])
        if args.json:
            cmd.append("--json")
        return run_script(cmd)

    # --- pipeline: 選択 HTML を validate → convert prepare まで流す ---
    if args.action == "pipeline":
        if not args.path or not args.select:
            print("ERROR: フォルダと --select が必要です", file=sys.stderr)
            return 1
        cmd = [
            sys.executable,
            str(SCRIPTS / "intake" / "start_pipeline.py"),
            args.path,
            "--target-type",
            args.target_type,
            "--theme-slug",
            args.theme_slug,
            "--tool",
            args.tool,
        ]
        for sel in args.select:
            cmd.extend(["--select", sel])
        if args.package_name:
            cmd.extend(["--package-name", args.package_name])
        if args.session_id:
            cmd.extend(["--session-id", args.session_id])
        if args.notes:
            cmd.extend(["--notes", args.notes])
        # --agent 指定時は prepare 後に agent run まで連続実行
        if args.agent:
            cmd.append("--agent")
        if args.json:
            cmd.append("--json")
        return run_script(cmd)

    print(f"不明な intake アクション: {args.action}", file=sys.stderr)
    return 1


# ---------------------------------------------------------------------------
# convert … Claude Code 向け変換の準備 / 完了マーク（汎用 WP 経路）
# ---------------------------------------------------------------------------

def cmd_convert(args: argparse.Namespace) -> int:
    """convert サブコマンド。

    prepare   : intake からセッションを作り CLAUDE_INSTRUCTIONS.md を生成
    mark-done : Claude Code 変換後、wordpress/ の存在を確認して status=converted
    """
    if args.action == "prepare":
        cmd = [sys.executable, str(SCRIPTS / "convert" / "prepare_claude_input.py")]
        if args.target:
            cmd.append(args.target)
        if args.session_id:
            cmd.extend(["--session-id", args.session_id])
        return run_script(cmd)
    if args.action == "mark-done":
        # mark-done では target 位置引数がセッション ID
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


# ---------------------------------------------------------------------------
# validate / quality / visual … 変換後の検査系
# ---------------------------------------------------------------------------

def cmd_validate(args: argparse.Namespace) -> int:
    """変換後ファイルの基本検証（必須ファイル・PHP 構文など）。

    結果は output/<session>/validation.json に保存される。
    deploy staging は valid=true を前提とする。
    """
    cmd = [sys.executable, str(SCRIPTS / "validate" / "run_validation.py"), args.session_id]
    if args.json:
        cmd.append("--json")
    return run_script(cmd)


def cmd_quality(args: argparse.Namespace) -> int:
    """品質ゲート（HTML / SEO / a11y / security / perf）。

    --stage でゲートセットを切り替え（既定: pr_merge）。
    blocking 失敗時はデプロイしない運用を想定。
    """
    cmd = [sys.executable, str(SCRIPTS / "quality" / "run_gates.py"), args.session_id]
    if args.stage:
        cmd.extend(["--stage", args.stage])
    if args.json:
        cmd.append("--json")
    return run_script(cmd)


def cmd_visual(args: argparse.Namespace) -> int:
    """Playwright によるビジュアル回帰テスト。

    初回やベースライン更新時は --update を付ける。
    差分は output/<session>/visual/{baseline,current,diff}/ に保存。
    """
    cmd = [sys.executable, str(SCRIPTS / "visual" / "run_regression.py"), args.session_id]
    if args.env:
        cmd.extend(["--env", args.env])
    if args.update:
        cmd.append("--update")
    if args.json:
        cmd.append("--json")
    return run_script(cmd)


# ---------------------------------------------------------------------------
# git … PR / コミット / Git 経由デプロイ・ロールバック
# ---------------------------------------------------------------------------

def cmd_git(args: argparse.Namespace) -> int:
    """Git 関連操作の振り分け。

    pr / commit / push は Python スクリプト。
    deploy / rollback（via git）は bash スクリプト（SSH/CI 想定）。
    """
    if args.action == "pr":
        cmd = [sys.executable, str(SCRIPTS / "git" / "create_pr.py"), args.session_id]
        if args.base:
            cmd.extend(["--base", args.base])
        return run_script(cmd)
    if args.action in {"commit", "push"}:
        if not args.session_id:
            print("ERROR: session_id が必要です", file=sys.stderr)
            return 1
        cmd = [sys.executable, str(SCRIPTS / "git" / "commit_push.py"), args.session_id]
        if args.message:
            cmd.extend(["--message", args.message])
        if args.branch:
            cmd.extend(["--branch", args.branch])
        # commit のみ（--push なし）のときはリモートへ送らない
        if args.action == "commit" and not args.push:
            cmd.append("--no-push")
        if args.pr:
            cmd.append("--pr")
        if args.base:
            cmd.extend(["--base", args.base])
        if args.json:
            cmd.append("--json")
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


# ---------------------------------------------------------------------------
# knowledge / ai / agent … RAG・マルチAI・自律オーケストレーション
# ---------------------------------------------------------------------------

def cmd_knowledge(args: argparse.Namespace) -> int:
    """RAG ナレッジベースのインデックス構築 / 検索。

    変換前に retrieve すると Claude Code 等の出力品質が安定しやすい。
    """
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
    """マルチ AI ルーター。

    config/ai-providers.yaml のステージ設定に従い、
    Claude Code / OpenAI / Copilot などへ振り分ける。
    list は利用可否一覧、route は実実行（多くは手動指示ファイル生成）。
    """
    if args.action == "list":
        # router.py は --stage/--session 必須のためダミー値を渡す
        return run_script([sys.executable, str(SCRIPTS / "ai" / "router.py"), "--list",
                           "--stage", "wp_conversion", "--session", "none"])
    cmd = [sys.executable, str(SCRIPTS / "ai" / "router.py"),
           "--stage", args.stage, "--session", args.session]
    if args.prompt:
        cmd.extend(["--prompt", args.prompt])
    # Claude CLI 等が入っていれば自動実行を試行
    if args.auto_cli:
        cmd.append("--auto-cli")
    return run_script(cmd)


def cmd_agent(args: argparse.Namespace) -> int:
    """AI エージェント自律実行。

    workflow/pipeline.yaml のステージを順に実行する。
    Claude Code 変換など手動ステージでは一時停止し、
    resume / --approve で再開・本番承認する。
    """
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


# ---------------------------------------------------------------------------
# deploy / rollback … 環境への反映と復旧
# ---------------------------------------------------------------------------

def cmd_deploy(args: argparse.Namespace) -> int:
    """デプロイ。

    staging  : 既定は Python のローカル配置（Docker WP / staging/ ディレクトリ）
    production: bash スクリプト（--confirm 必須想定）
    --via-git : Git ベースのデプロイ経路へ切り替え
    """
    if args.via_git:
        bash_cmd = ["bash", str(SCRIPTS / "git" / "deploy_via_git.sh"), args.env, args.session_id]
        if args.confirm:
            bash_cmd.append("--confirm")
        return run_script(bash_cmd)
    if args.env == "staging":
        # Windows / ローカル Docker 向け Python デプロイ（SSH不要）
        cmd = [sys.executable, str(SCRIPTS / "deploy" / "deploy_staging_local.py"), args.session_id]
        if args.dry_run:
            cmd.append("--dry-run")
        return run_script(cmd)
    cmd = ["bash", str(SCRIPTS / "deploy" / "deploy_production.sh"), args.session_id]
    if args.confirm:
        cmd.append("--confirm")
    return run_script(cmd)


def cmd_rollback(args: argparse.Namespace) -> int:
    """ロールバック。本番障害時の復旧用。--confirm を付けて実行する。"""
    if args.via_git:
        bash_cmd = ["bash", str(SCRIPTS / "git" / "rollback_git.sh"), args.session_id, args.env]
        if args.confirm:
            bash_cmd.append("--confirm")
        return run_script(bash_cmd)
    cmd = ["bash", str(SCRIPTS / "rollback" / "rollback.sh"), args.session_id, args.env]
    if args.confirm:
        cmd.append("--confirm")
    return run_script(cmd)


# ---------------------------------------------------------------------------
# db / test / analyze / swell / report / status … 補助・一括系
# ---------------------------------------------------------------------------

def cmd_db(args: argparse.Namespace) -> int:
    """PostgreSQL へのセッション同期（Railway 等で DATABASE_URL 利用時）。"""
    cmd = [sys.executable, str(SCRIPTS / "db" / "sync_sessions.py"), args.action]
    if args.session_id:
        cmd.append(args.session_id)
    if args.json:
        cmd.append("--json")
    return run_script(cmd)


def cmd_test(args: argparse.Namespace) -> int:
    """ユニットテストの実行・履歴一覧・詳細表示。

    Web UI の /tests からも同じスクリプトが呼ばれる。
    """
    cmd = [sys.executable, str(SCRIPTS / "test" / "run_tests.py"), args.action]
    if args.action == "run":
        if args.path:
            cmd.extend(["--path", args.path])
        if args.keyword:
            # pytest -k 相当のキーワードフィルタ
            cmd.extend(["-k", args.keyword])
    elif args.action == "list":
        cmd.extend(["--limit", str(args.limit)])
    elif args.action == "show":
        cmd.append(args.run_id or "latest")
    if args.json:
        cmd.append("--json")
    return run_script(cmd)


def cmd_analyze(args: argparse.Namespace) -> int:
    """HTML 構造・コンポーネント解析。

    セッション ID または HTML フォルダを渡し、structure.json を生成する。
    SWELL 変換の前段としても使われる。
    """
    cmd = [sys.executable, str(SCRIPTS / "analyze" / "html_structure.py"), args.target]
    if args.out:
        cmd.extend(["--out", args.out])
    if args.json:
        cmd.append("--json")
    return run_script(cmd)


def cmd_swell(args: argparse.Namespace) -> int:
    """SWELL 子テーマ向け変換。

    convert  : 既存セッションの HTML を子テーマ / blocks / template-parts へ変換
    pipeline : intake〜analyze〜convert〜validate〜deploy〜visual〜report の一連実行

    Claude Code 経路とは別の「自動変換」ルート。
    """
    # 位置引数 session_id と --session-id の両方を許容
    session_id = args.session_id or getattr(args, "session_id_opt", None)
    if args.action == "convert":
        if not session_id:
            print("ERROR: session_id が必要です", file=sys.stderr)
            return 1
        cmd = [
            sys.executable,
            str(SCRIPTS / "swell" / "convert_to_swell.py"),
            session_id,
            "--theme-slug",
            args.theme_slug,
            "--parent-theme",
            args.parent_theme,
        ]
        if args.json:
            cmd.append("--json")
        return run_script(cmd)

    if args.action == "pipeline":
        cmd = [sys.executable, str(SCRIPTS / "swell" / "run_pipeline.py")]
        if session_id:
            cmd.append(session_id)
        if args.source_dir:
            cmd.extend(["--source-dir", args.source_dir])
        # --select 未指定時は空リスト（ソース内全 HTML 等はスクリプト側で扱う）
        for sel in args.select or []:
            cmd.extend(["--select", sel])
        cmd.extend(["--theme-slug", args.theme_slug, "--parent-theme", args.parent_theme])
        if args.skip_git:
            cmd.append("--skip-git")
        if args.skip_deploy:
            cmd.append("--skip-deploy")
        if args.skip_visual:
            cmd.append("--skip-visual")
        if args.push:
            cmd.append("--push")
        if args.pr:
            cmd.append("--pr")
        # 初回 visual はベースライン作成のため --visual-update を推奨
        if args.visual_update:
            cmd.append("--visual-update")
        if args.json:
            cmd.append("--json")
        return run_script(cmd)

    print(f"不明な swell アクション: {args.action}", file=sys.stderr)
    return 1


def cmd_report(args: argparse.Namespace) -> int:
    """変更レポート（change_report.md / .json）を生成する。"""
    cmd = [sys.executable, str(SCRIPTS / "report" / "generate_report.py"), args.session_id]
    if args.json:
        cmd.append("--json")
    return run_script(cmd)


def cmd_status(args: argparse.Namespace) -> int:
    """セッション一覧を表示する。

    DATABASE_URL があれば PostgreSQL を優先し、失敗時や --local 時は
    ローカルの output/ ディレクトリを走査する。
    """
    # DATABASE_URL がある場合は Postgres 優先
    try:
        sys.path.insert(0, str(SCRIPTS))
        from lib.session_store import database_url, list_sessions

        if database_url() and not getattr(args, "local", False):
            rows = list_sessions()
            if not rows:
                print("セッションなし（PostgreSQL）")
                return 0
            print(f"{'Session ID':<20} {'Status':<22} {'Agent':<12} {'Target':<12}")
            print("-" * 68)
            for r in rows:
                print(f"{r['id']:<20} {r['status']:<22} {r['agent']:<12} {r['target']:<12}")
            return 0
    except Exception as e:  # noqa: BLE001
        # DB 未設定・接続失敗時はローカルへフォールバック
        print(f"[db] fallback to local: {e}", file=sys.stderr)

    output_dir = ROOT / "output"
    if not output_dir.exists():
        print("セッションなし")
        return 0

    # 更新日時の新しい順
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
        agent_status = "-"
        if agent_file.exists():
            agent_status = json.loads(agent_file.read_text(encoding="utf-8")).get("status", "?")
        print(f"{s.name:<20} {status:<22} {agent_status:<12} {target:<12}")
    return 0


# ---------------------------------------------------------------------------
# main … 引数定義とコマンドディスパッチ
# ---------------------------------------------------------------------------

def main() -> int:
    """CLI のエントリ。サブパーサを定義し、対応する cmd_* へ委譲する。"""
    parser = argparse.ArgumentParser(
        description="WPAIPublisher - AI出力をWordPressへ反映するワークフロー",
        # モジュール docstring（使用例）をヘルプ末尾にそのまま出す
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    sub = parser.add_subparsers(dest="command")

    # --- intake ---
    p_intake = sub.add_parser("intake", help="AI出力の受け取り / HTML選択")
    p_intake.add_argument(
        "action",
        choices=["validate", "list", "select", "pipeline"],
        help="validate | list | select | pipeline",
    )
    p_intake.add_argument("path", nargs="?", help="intake または HTML ソースフォルダ")
    # action=append: --select を複数回指定可能
    p_intake.add_argument("--select", action="append", help="処理する HTML 相対パス（複数可）")
    p_intake.add_argument("--interactive", action="store_true", help="対話的に HTML を選択")
    p_intake.add_argument("--package-name", help="intake パッケージ名")
    p_intake.add_argument("--session-id", help="pipeline 時のセッションID")
    p_intake.add_argument(
        "--target-type",
        default="page",
        choices=["page", "block", "theme", "template-part", "custom-css"],
    )
    p_intake.add_argument("--theme-slug", default="custom-theme")
    p_intake.add_argument("--tool", default="other", choices=["codex", "cursor", "copilot", "other"])
    p_intake.add_argument("--notes", default="")
    p_intake.add_argument("--agent", action="store_true", help="pipeline 後に agent run")
    p_intake.add_argument("--json", action="store_true")

    # --- convert（Claude Code 経路） ---
    p_convert = sub.add_parser("convert", help="AI変換")
    p_convert.add_argument("action", choices=["prepare", "mark-done"])
    p_convert.add_argument("target", nargs="?", help="intakeディレクトリまたはセッションID")
    p_convert.add_argument("--session-id", help="セッションID指定（prepare時）")
    p_convert.add_argument("--notes", help="変換メモ")

    # --- validate / quality / visual ---
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

    # --- git ---
    p_git = sub.add_parser("git", help="Git CI/CD")
    p_git.add_argument("action", choices=["pr", "commit", "push", "deploy", "rollback"])
    p_git.add_argument("session_id", nargs="?")
    p_git.add_argument("--env", default="staging", choices=["staging", "production"])
    p_git.add_argument("--base", default="staging")
    p_git.add_argument("--confirm", action="store_true")
    p_git.add_argument("--message", "-m", help="コミットメッセージ")
    p_git.add_argument("--branch", help="ブランチ名")
    p_git.add_argument("--push", action="store_true", help="commit 後に push")
    p_git.add_argument("--pr", action="store_true", help="commit/push 後に PR 作成")
    p_git.add_argument("--json", action="store_true")

    # --- analyze / swell / report ---
    p_analyze = sub.add_parser("analyze", help="HTML 構造・コンポーネント解析")
    p_analyze.add_argument("target", help="セッションID または HTML フォルダ")
    p_analyze.add_argument("--out", help="出力 JSON")
    p_analyze.add_argument("--json", action="store_true")

    p_swell = sub.add_parser("swell", help="SWELL 変換・一連パイプライン")
    p_swell.add_argument("action", choices=["convert", "pipeline"])
    p_swell.add_argument("session_id", nargs="?", help="セッションID")
    # 位置引数とフラグの両方でセッション指定できるようにする
    p_swell.add_argument("--session-id", dest="session_id_opt", help="セッションID（別名）")
    p_swell.add_argument("--source-dir", help="HTML フォルダ（pipeline）")
    p_swell.add_argument("--select", action="append", help="HTML 相対パス")
    p_swell.add_argument("--theme-slug", default="swell-child")
    p_swell.add_argument("--parent-theme", default="swell")
    p_swell.add_argument("--skip-git", action="store_true")
    p_swell.add_argument("--skip-deploy", action="store_true")
    p_swell.add_argument("--skip-visual", action="store_true")
    p_swell.add_argument("--push", action="store_true")
    p_swell.add_argument("--pr", action="store_true")
    p_swell.add_argument("--visual-update", action="store_true")
    p_swell.add_argument("--json", action="store_true")

    p_report = sub.add_parser("report", help="変更レポート生成")
    p_report.add_argument("action", choices=["generate"])
    p_report.add_argument("session_id")
    p_report.add_argument("--json", action="store_true")

    # --- knowledge / ai / agent ---
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

    # --- deploy / rollback ---
    p_deploy = sub.add_parser("deploy", help="デプロイ")
    p_deploy.add_argument("env", choices=["staging", "production"])
    p_deploy.add_argument("session_id")
    p_deploy.add_argument("--confirm", action="store_true")
    p_deploy.add_argument("--via-git", action="store_true", help="Gitベースデプロイ")
    p_deploy.add_argument("--dry-run", action="store_true", help="ステージングのドライラン")

    p_rollback = sub.add_parser("rollback", help="ロールバック")
    p_rollback.add_argument("session_id")
    p_rollback.add_argument("env", choices=["staging", "production"], default="production", nargs="?")
    p_rollback.add_argument("--confirm", action="store_true")
    p_rollback.add_argument("--via-git", action="store_true")

    # --- db / test / status ---
    p_db = sub.add_parser("db", help="PostgreSQL セッション同期")
    p_db.add_argument("action", choices=["sync", "list", "push"])
    p_db.add_argument("session_id", nargs="?", help="push 時のセッションID")
    p_db.add_argument("--json", action="store_true")

    p_test = sub.add_parser("test", help="ユニットテスト実行・結果確認")
    p_test.add_argument("action", choices=["run", "list", "show"])
    p_test.add_argument("run_id", nargs="?", default="latest", help="show 時の実行ID")
    p_test.add_argument("--path", default="tests", help="テストパス")
    p_test.add_argument("-k", "--keyword", help="pytest -k フィルタ")
    p_test.add_argument("--limit", type=int, default=20, help="list 件数")
    p_test.add_argument("--json", action="store_true")

    p_status = sub.add_parser("status", help="セッション一覧")
    p_status.add_argument("--local", action="store_true", help="ローカル output/ のみ表示")

    args = parser.parse_args()
    # サブコマンド未指定時はヘルプを出して正常終了
    if not args.command:
        parser.print_help()
        return 0

    # コマンド名 → ハンドラ関数の対応表
    handlers = {
        "intake": cmd_intake,
        "convert": cmd_convert,
        "validate": cmd_validate,
        "quality": cmd_quality,
        "visual": cmd_visual,
        "git": cmd_git,
        "analyze": cmd_analyze,
        "swell": cmd_swell,
        "report": cmd_report,
        "knowledge": cmd_knowledge,
        "ai": cmd_ai,
        "agent": cmd_agent,
        "deploy": cmd_deploy,
        "rollback": cmd_rollback,
        "db": cmd_db,
        "test": cmd_test,
        "status": cmd_status,
    }
    return handlers[args.command](args)


if __name__ == "__main__":
    # プロセス終了コードとして main の戻り値を返す（CI / シェル判定用）
    sys.exit(main())
