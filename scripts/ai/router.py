#!/usr/bin/env python3
"""マルチAIルーター — ステージに応じて最適なAIプロバイダーを選択・実行"""

import argparse
import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))

from lib.config import get_session_dir, load_ai_providers  # noqa: E402
from ai.providers.base import BaseProvider, ProviderResult  # noqa: E402
from ai.providers.openai_provider import OpenAIProvider  # noqa: E402
from ai.providers.claude_provider import ClaudeCodeProvider  # noqa: E402
from ai.providers.copilot_provider import CopilotProvider  # noqa: E402

PROVIDER_CLASSES: dict[str, type[BaseProvider]] = {
    "openai": OpenAIProvider,
    "anthropic": ClaudeCodeProvider,
    "github": CopilotProvider,
}


def create_provider(name: str, config: dict, root: Path) -> BaseProvider:
    provider_type = config.get("type", "openai")
    cls = PROVIDER_CLASSES.get(provider_type, OpenAIProvider)
    return cls(name, config, root)


def resolve_provider(stage: str, ai_config: dict) -> tuple[str, str | None]:
    """ステージに対応するプロバイダー名とフォールバックを返す"""
    pipeline = ai_config.get("pipeline", {})
    stage_config = pipeline.get(stage, {})
    provider = stage_config.get("provider", "claude_code")
    fallback = stage_config.get("fallback")
    return provider, fallback


def build_context(session_id: str, root: Path) -> dict[str, Any]:
    session_dir = get_session_dir(session_id)
    context: dict[str, Any] = {
        "session_id": session_id,
        "session_dir": str(session_dir),
        "root": str(root),
    }
    task_path = session_dir / "task.json"
    if task_path.exists():
        context["task_json"] = task_path.read_text(encoding="utf-8")

    rag_path = session_dir / "rag_context.md"
    if rag_path.exists():
        context["rag_context"] = rag_path.read_text(encoding="utf-8")

    source_dir = session_dir / "source"
    if source_dir.exists():
        context["source_files"] = "\n".join(
            str(f.relative_to(source_dir)) for f in source_dir.rglob("*") if f.is_file()
        )
    return context


def execute_stage(
    stage: str,
    prompt_path: Path,
    session_id: str,
    auto_cli: bool = False,
) -> ProviderResult:
    ai_config = load_ai_providers()
    provider_name, fallback_name = resolve_provider(stage, ai_config)
    providers_config = ai_config.get("providers", {})

    prompt = prompt_path.read_text(encoding="utf-8") if prompt_path.exists() else ""
    context = build_context(session_id, ROOT)
    context["auto_cli"] = auto_cli

    for name in [provider_name, fallback_name]:
        if not name:
            continue
        config = providers_config.get(name)
        if not config:
            continue
        provider = create_provider(name, config, ROOT)
        if not provider.is_available():
            print(f"[router] {name} は利用不可、スキップ", file=sys.stderr)
            continue

        print(f"[router] {stage} → {name}", file=sys.stderr)
        result = provider.execute(stage, prompt, context)
        if result.success or result.requires_manual:
            return result

    return ProviderResult(
        success=False,
        provider="none",
        requires_manual=True,
        output="利用可能なプロバイダーがありません",
    )


def list_providers() -> None:
    ai_config = load_ai_providers()
    providers = ai_config.get("providers", {})
    pipeline = ai_config.get("pipeline", {})

    print(f"{'Stage':<20} {'Provider':<15} {'Fallback':<15} {'Available'}")
    print("-" * 65)
    for stage, cfg in pipeline.items():
        pname = cfg.get("provider", "?")
        fb = cfg.get("fallback", "-")
        pconfig = providers.get(pname, {})
        provider = create_provider(pname, pconfig, ROOT)
        avail = "yes" if provider.is_available() else "no"
        print(f"{stage:<20} {pname:<15} {fb:<15} {avail}")


def main() -> int:
    parser = argparse.ArgumentParser(description="マルチAIルーター")
    parser.add_argument("--stage", required=True, help="パイプラインステージ名")
    parser.add_argument("--session", required=True, help="セッションID")
    parser.add_argument("--prompt", default="prompts/convert-to-wp.md", help="プロンプトファイル")
    parser.add_argument("--auto-cli", action="store_true", help="CLI自動実行を試行")
    parser.add_argument("--list", action="store_true", help="プロバイダー一覧")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    if args.list:
        list_providers()
        return 0

    prompt_path = ROOT / args.prompt
    result = execute_stage(args.stage, prompt_path, args.session, args.auto_cli)

    output = {
        "success": result.success,
        "provider": result.provider,
        "requires_manual": result.requires_manual,
        "output": result.output,
        "instructions_path": str(result.instructions_path) if result.instructions_path else None,
    }

    if args.json:
        print(json.dumps(output, indent=2, ensure_ascii=False))
    else:
        print(f"Provider: {result.provider}")
        print(f"Success: {result.success}")
        if result.requires_manual:
            print(f"Manual: {result.output}")
        if result.instructions_path:
            print(f"Instructions: {result.instructions_path}")

    return 0 if result.success else 1


if __name__ == "__main__":
    sys.exit(main())
