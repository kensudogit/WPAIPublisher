#!/usr/bin/env python3
"""REST API 経由で固定ページを更新"""

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))

from lib.config import get_env_config, get_output_dir  # noqa: E402
from lib.wp_api import WPApiClient, WPApiError  # noqa: E402


def load_page_content(wp_dir: Path) -> str:
    for pattern in ("*.html", "content.html", "page.html", "*.php"):
        files = list(wp_dir.glob(pattern))
        if files:
            return files[0].read_text(encoding="utf-8")
    raise FileNotFoundError(f"ページコンテンツが見つかりません: {wp_dir}")


def main() -> int:
    parser = argparse.ArgumentParser(description="固定ページをREST APIで更新")
    parser.add_argument("--env", required=True, choices=["staging", "production"])
    parser.add_argument("--session", required=True)
    parser.add_argument("--status", default="draft", choices=["draft", "publish", "private"])
    args = parser.parse_args()

    session_dir = get_output_dir() / args.session
    task_path = session_dir / "task.json"
    wp_dir = session_dir / "wordpress"

    with open(task_path, encoding="utf-8") as f:
        task = json.load(f)

    target = task["manifest"]["target"]
    page_slug = target.get("page_slug", "new-page")
    content = load_page_content(wp_dir)

    env = get_env_config(args.env)
    if not all([env["url"], env["user"], env["app_password"]]):
        print(f"ERROR: {args.env} の REST API 設定が不完全です", file=sys.stderr)
        return 1

    client = WPApiClient(env["url"], env["user"], env["app_password"])

    if not client.health_check():
        print(f"ERROR: WordPress API に接続できません: {env['url']}", file=sys.stderr)
        return 1

    try:
        page = client.get_page_by_slug(page_slug)
        if page:
            result = client.update_page_content(page["id"], content, args.status)
            print(f"ページ更新: ID={result['id']} slug={page_slug} status={args.status}")
        else:
            title = page_slug.replace("-", " ").title()
            result = client.create_page(title, page_slug, content, args.status)
            print(f"ページ作成: ID={result['id']} slug={page_slug} status={args.status}")
    except WPApiError as e:
        print(f"ERROR: API エラー - {e}", file=sys.stderr)
        if e.body:
            print(e.body, file=sys.stderr)
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
