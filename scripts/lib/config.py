#!/usr/bin/env python3
"""設定ファイル・環境変数の読み込み"""

import os
from pathlib import Path
from typing import Any

import yaml

ROOT = Path(__file__).resolve().parents[2]


def load_env_file(env_path: Path | None = None) -> dict[str, str]:
    """.env ファイルを読み込む（python-dotenv不要の簡易実装）"""
    env_path = env_path or ROOT / "config" / ".env"
    result: dict[str, str] = {}
    if not env_path.exists():
        return result
    for line in env_path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        if "=" in line:
            key, _, value = line.partition("=")
            result[key.strip()] = value.strip().strip('"').strip("'")
    return result


def load_config(config_path: Path | None = None) -> dict[str, Any]:
    """environments.yaml を読み込む"""
    config_path = config_path or ROOT / "config" / "environments.yaml"
    if not config_path.exists():
        example = ROOT / "config" / "environments.example.yaml"
        if example.exists():
            raise FileNotFoundError(
                f"設定ファイルが見つかりません: {config_path}\n"
                f"コピーしてください: cp config/environments.example.yaml config/environments.yaml"
            )
        raise FileNotFoundError(f"設定ファイルが見つかりません: {config_path}")
    with open(config_path, encoding="utf-8") as f:
        return yaml.safe_load(f)


def get_env_config(env_name: str) -> dict[str, str]:
    """環境名（staging/production）に対応するREST API設定を返す"""
    env_vars = {**os.environ, **load_env_file()}
    prefix = "WP_STAGING" if env_name == "staging" else "WP_PROD"
    return {
        "url": env_vars.get(f"{prefix}_URL", ""),
        "user": env_vars.get(f"{prefix}_USER", ""),
        "app_password": env_vars.get(f"{prefix}_APP_PASSWORD", ""),
        "ssh": env_vars.get(f"{prefix}_SSH", ""),
        "path": env_vars.get(f"{prefix}_PATH", ""),
    }


def get_output_dir() -> Path:
    return ROOT / "output"


def get_intake_dir() -> Path:
    return ROOT / "intake"


def get_deployments_dir() -> Path:
    d = ROOT / "deployments"
    d.mkdir(exist_ok=True)
    return d


def load_yaml_config(name: str) -> dict[str, Any]:
    """config/<name>.yaml を読み込む（example からのフォールバック付き）"""
    config_path = ROOT / "config" / f"{name}.yaml"
    if not config_path.exists():
        example = ROOT / "config" / f"{name}.example.yaml"
        if example.exists():
            with open(example, encoding="utf-8") as f:
                return yaml.safe_load(f)
        raise FileNotFoundError(f"設定ファイルが見つかりません: {config_path}")
    with open(config_path, encoding="utf-8") as f:
        return yaml.safe_load(f)


def load_ai_providers() -> dict[str, Any]:
    return load_yaml_config("ai-providers")


def load_quality_gates() -> dict[str, Any]:
    return load_yaml_config("quality-gates")


def get_knowledge_dir() -> Path:
    d = ROOT / "knowledge"
    d.mkdir(exist_ok=True)
    return d


def get_session_dir(session_id: str) -> Path:
    return get_output_dir() / session_id
