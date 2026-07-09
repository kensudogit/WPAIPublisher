#!/usr/bin/env python3
"""カスタムCSSを WordPress Customizer 経由で反映（REST API）"""

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))

from lib.config import get_env_config, get_output_dir  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description="カスタムCSSのデプロイ")
    parser.add_argument("--env", required=True, choices=["staging", "production"])
    parser.add_argument("--session", required=True)
    args = parser.parse_args()

    session_dir = get_output_dir() / args.session
    wp_dir = session_dir / "wordpress"

    css_files = list(wp_dir.glob("*.css")) + list(wp_dir.glob("**/*.css"))
    if not css_files:
        print("ERROR: CSSファイルが見つかりません", file=sys.stderr)
        return 1

    css_content = "\n".join(f.read_text(encoding="utf-8") for f in css_files)

    env = get_env_config(args.env)
    output_file = ROOT / "deployments" / f"custom-css-{args.env}-{args.session}.css"
    output_file.parent.mkdir(exist_ok=True)
    output_file.write_text(css_content, encoding="utf-8")

    print(f"カスタムCSSを生成: {output_file}")
    print(f"環境: {args.env} ({env.get('url', '未設定')})")
    print("")
    print("以下のいずれかで反映してください:")
    print("  1. WP-CLI: wp option patch update theme_mods_<theme> custom_css '<css>'")
    print("  2. 管理画面: 外観 > カスタマイズ > 追加CSS")
    print("  3. Additional CSS プラグインの REST API エンドポイント")

    return 0


if __name__ == "__main__":
    sys.exit(main())
