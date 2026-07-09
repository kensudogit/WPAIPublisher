#!/usr/bin/env python3
"""OpenAI API プロバイダー（ChatGPT / Codex）"""

import json
import os
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any

from .base import BaseProvider, ProviderResult


class OpenAIProvider(BaseProvider):
    def is_available(self) -> bool:
        key = self.config.get("env_key", "OPENAI_API_KEY")
        return bool(os.environ.get(key) or self._load_env().get(key))

    def _load_env(self) -> dict[str, str]:
        env_path = self.root / "config" / ".env"
        result = {}
        if env_path.exists():
            for line in env_path.read_text(encoding="utf-8").splitlines():
                if "=" in line and not line.strip().startswith("#"):
                    k, _, v = line.partition("=")
                    result[k.strip()] = v.strip().strip('"')
        return result

    def execute(self, stage: str, prompt: str, context: dict[str, Any]) -> ProviderResult:
        key_name = self.config.get("env_key", "OPENAI_API_KEY")
        api_key = os.environ.get(key_name) or self._load_env().get(key_name)
        if not api_key:
            return ProviderResult(
                success=False,
                provider=self.name,
                requires_manual=True,
                output=f"{key_name} が未設定です",
            )

        provider_prompt = self.load_provider_prompt(stage)
        full_prompt = f"{provider_prompt}\n\n---\n\n{prompt}" if provider_prompt else prompt

        if context.get("rag_context"):
            full_prompt = f"## 参考ナレッジ\n{context['rag_context']}\n\n---\n\n{full_prompt}"

        model = self.config.get("model", "gpt-4o")
        try:
            response = self._call_api(api_key, model, full_prompt, context)
            return ProviderResult(success=True, provider=self.name, output=response)
        except Exception as e:
            return ProviderResult(success=False, provider=self.name, output=str(e))

    def _call_api(self, api_key: str, model: str, prompt: str, context: dict) -> str:
        url = "https://api.openai.com/v1/chat/completions"
        messages = [{"role": "user", "content": prompt}]
        if context.get("system_prompt"):
            messages.insert(0, {"role": "system", "content": context["system_prompt"]})

        body = json.dumps({
            "model": model,
            "messages": messages,
            "temperature": 0.2,
        }).encode()

        req = urllib.request.Request(
            url,
            data=body,
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=120) as resp:
            data = json.loads(resp.read().decode())
            return data["choices"][0]["message"]["content"]
