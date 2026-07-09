#!/usr/bin/env python3
"""GitHub Copilot プロバイダー（IDE手動実行）"""

from pathlib import Path
from typing import Any

from .base import BaseProvider, ProviderResult


class CopilotProvider(BaseProvider):
    """Copilot はAPI直接呼び出し不可。IDE内チャット用の指示ファイルを生成する。"""

    def is_available(self) -> bool:
        return True  # IDE拡張は常に手動利用可能とみなす

    def execute(self, stage: str, prompt: str, context: dict[str, Any]) -> ProviderResult:
        session_dir = Path(context.get("session_dir", "."))
        session_dir.mkdir(parents=True, exist_ok=True)
        instructions_path = session_dir / f"COPILOT_INSTRUCTIONS_{stage}.md"

        provider_prompt = self.load_provider_prompt(stage)
        content = f"""# GitHub Copilot Chat タスク: {stage}

> Copilot Chat（VS Code / Cursor）に以下を貼り付けて実行してください。

## プロバイダー固有指示
{provider_prompt}

## タスク
{prompt}

## 対象ファイル
{context.get('source_files', '（task.json を参照）')}

## RAG参考
{context.get('rag_context', '（なし）')}
"""
        instructions_path.write_text(content, encoding="utf-8")

        return ProviderResult(
            success=True,
            provider=self.name,
            requires_manual=True,
            instructions_path=instructions_path,
            output=f"Copilot Chat で実行: {instructions_path}",
        )
