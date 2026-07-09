#!/usr/bin/env python3
"""Claude Code プロバイダー（CLI / IDE）"""

import os
import shutil
import subprocess
from pathlib import Path
from typing import Any

from .base import BaseProvider, ProviderResult


class ClaudeCodeProvider(BaseProvider):
    def is_available(self) -> bool:
        cli = self.config.get("cli_command", "claude")
        return shutil.which(cli) is not None or bool(
            os.environ.get(self.config.get("env_key", "ANTHROPIC_API_KEY"))
        )

    def execute(self, stage: str, prompt: str, context: dict[str, Any]) -> ProviderResult:
        session_dir = context.get("session_dir")
        if session_dir:
            instructions_dir = Path(session_dir)
            instructions_dir.mkdir(parents=True, exist_ok=True)
            instructions_path = instructions_dir / f"AI_INSTRUCTIONS_{stage}.md"

            provider_prompt = self.load_provider_prompt(stage)
            content = f"""# Claude Code タスク: {stage}

## プロバイダー
Claude Code ({self.config.get('model', 'default')})

## プロバイダー固有指示
{provider_prompt}

## タスクプロンプト
{prompt}

## コンテキスト
```json
{context.get('task_json', '{}')}
```

## RAGコンテキスト
{context.get('rag_context', '（なし）')}

## 完了後
変換が完了したら以下を実行:
```
python wpaipublish.py convert mark-done {context.get('session_id', '<session_id>')}
```
"""
            instructions_path.write_text(content, encoding="utf-8")

            cli = self.config.get("cli_command", "claude")
            if shutil.which(cli) and context.get("auto_cli"):
                return self._run_cli(cli, instructions_path, context)

            return ProviderResult(
                success=True,
                provider=self.name,
                requires_manual=True,
                instructions_path=instructions_path,
                output=f"手動実行: Claude Code で {instructions_path} を開いて実行してください",
            )

        return ProviderResult(
            success=False,
            provider=self.name,
            requires_manual=True,
            output="session_dir が未設定です",
        )

    def _run_cli(self, cli: str, instructions_path: Path, context: dict) -> ProviderResult:
        try:
            result = subprocess.run(
                [cli, "-p", instructions_path.read_text(encoding="utf-8")],
                capture_output=True,
                text=True,
                timeout=600,
                cwd=str(context.get("root", ".")),
            )
            return ProviderResult(
                success=result.returncode == 0,
                provider=self.name,
                output=result.stdout or result.stderr,
                requires_manual=result.returncode != 0,
            )
        except (subprocess.TimeoutExpired, FileNotFoundError) as e:
            return ProviderResult(
                success=False,
                provider=self.name,
                requires_manual=True,
                instructions_path=instructions_path,
                output=str(e),
            )
