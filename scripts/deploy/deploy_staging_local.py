#!/usr/bin/env python3
"""ローカル / リモート共通のステージングデプロイ（Windows対応）"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))

from lib.config import get_output_dir, load_env_file  # noqa: E402


def load_env() -> dict[str, str]:
    return {**os.environ, **load_env_file()}


def session_ready(session_id: str) -> Path:
    session_dir = get_output_dir() / session_id
    validation = session_dir / "validation.json"
    if not session_dir.exists():
        raise SystemExit(f"ERROR: セッションが見つかりません: {session_id}")
    if not validation.exists():
        raise SystemExit("ERROR: 検証が未実行です。先に validate run を実行してください")
    data = json.loads(validation.read_text(encoding="utf-8"))
    if not data.get("valid"):
        raise SystemExit(f"ERROR: 検証が失敗しています: {session_id}")
    return session_dir


def snapshot(session_id: str, wp_dir: Path) -> Path:
    stamp = datetime.now().strftime("%Y%m%d%H%M%S")
    dest = ROOT / "deployments" / f"{session_id}-staging-{stamp}"
    dest.mkdir(parents=True, exist_ok=True)
    for item in wp_dir.iterdir():
        target = dest / item.name
        if item.is_dir():
            shutil.copytree(item, target, dirs_exist_ok=True)
        else:
            shutil.copy2(item, target)
    return dest


def record(session_id: str, snapshot_dir: Path) -> None:
    history = ROOT / "deployments" / "history.jsonl"
    history.parent.mkdir(exist_ok=True)
    entry = {
        "session_id": session_id,
        "env": "staging",
        "snapshot": str(snapshot_dir),
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
    with history.open("a", encoding="utf-8") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")


def deploy_local(wp_dir: Path, local_path: Path, target_type: str, theme_slug: str, block_name: str) -> Path:
    if target_type == "block":
        dest = local_path / "wp-content" / "themes" / theme_slug / "blocks" / block_name
    else:
        dest = local_path / "wp-content" / "themes" / theme_slug
    dest.mkdir(parents=True, exist_ok=True)
    for item in wp_dir.iterdir():
        if item.name == "preview.html":
            continue
        target = dest / item.name
        if item.is_dir():
            if target.exists():
                shutil.rmtree(target)
            shutil.copytree(item, target)
        else:
            shutil.copy2(item, target)
    return dest


def main() -> int:
    parser = argparse.ArgumentParser(description="ステージングデプロイ")
    parser.add_argument("session_id")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    env = load_env()
    session_dir = session_ready(args.session_id)
    wp_dir = session_dir / "wordpress"
    task = json.loads((session_dir / "task.json").read_text(encoding="utf-8"))
    target = task["manifest"]["target"]
    target_type = target["type"]
    theme_slug = target.get("theme_slug", "custom-theme")
    block_name = target.get("block_name", "block")

    snap = snapshot(args.session_id, wp_dir)
    print(f"[INFO] snapshot: {snap}")

    local_path = env.get("WP_STAGING_LOCAL_PATH", "").strip()
    if not local_path:
        # デフォルト: リポジトリ内 staging/
        local_path = str(ROOT / "staging")

    local_root = Path(local_path)
    print(f"[INFO] local staging root: {local_root}")

    if args.dry_run:
        print("[INFO] dry-run: ファイルコピーはスキップ")
    else:
        dest = deploy_local(wp_dir, local_root, target_type, theme_slug, block_name)
        print(f"[INFO] deployed files -> {dest}")

        # Docker が起動していればテーマ有効化を試行
        compose = ROOT / "docker-compose.staging.yml"
        if compose.exists():
            try:
                subprocess.run(
                    ["docker", "compose", "-f", str(compose), "exec", "-T", "wpcli",
                     "wp", "theme", "activate", theme_slug, "--allow-root"],
                    cwd=str(ROOT),
                    capture_output=True,
                    text=True,
                    timeout=60,
                    check=False,
                )
                subprocess.run(
                    ["docker", "compose", "-f", str(compose), "exec", "-T", "wpcli",
                     "wp", "cache", "flush", "--allow-root"],
                    cwd=str(ROOT),
                    capture_output=True,
                    text=True,
                    timeout=60,
                    check=False,
                )
            except (FileNotFoundError, subprocess.TimeoutExpired):
                print("[WARN] docker/wp-cli 未使用（ファイル配置のみ完了）")

    record(args.session_id, snap)

    task["status"] = "deployed_staging"
    task["staging_url"] = env.get("WP_STAGING_URL", "http://localhost:8088")
    task["staging_local_path"] = str(local_root)
    task["deployed_at"] = datetime.now(timezone.utc).isoformat()
    (session_dir / "task.json").write_text(json.dumps(task, indent=2, ensure_ascii=False), encoding="utf-8")

    from lib.sync_hook import sync_session  # noqa: E402

    sync_session(args.session_id)

    print("[INFO] ステージングデプロイ完了")
    print(f"[INFO] 確認URL: {task['staging_url']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
