#!/usr/bin/env python3
"""AIプロバイダー基底クラス"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


@dataclass
class ProviderResult:
    success: bool
    provider: str
    output: str = ""
    requires_manual: bool = False
    instructions_path: Path | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


class BaseProvider(ABC):
    def __init__(self, name: str, config: dict[str, Any], root: Path):
        self.name = name
        self.config = config
        self.root = root
        self.prompt_dir = root / config.get("prompt_dir", f"prompts/providers/{name}")

    @abstractmethod
    def is_available(self) -> bool:
        pass

    @abstractmethod
    def execute(self, stage: str, prompt: str, context: dict[str, Any]) -> ProviderResult:
        pass

    def load_provider_prompt(self, stage: str) -> str:
        prompt_file = self.prompt_dir / f"{stage}.md"
        if prompt_file.exists():
            return prompt_file.read_text(encoding="utf-8")
        return ""
