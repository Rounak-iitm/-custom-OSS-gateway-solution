"""Load and validate config.yaml into typed objects."""
from __future__ import annotations

import os
from pathlib import Path
from typing import Optional

import yaml
from pydantic import BaseModel


class ProviderConfig(BaseModel):
    kind: str  # "openai" | "anthropic" | "local"
    model: str
    api_key_env: Optional[str] = None
    base_url: Optional[str] = None  # for local/self-hosted (vLLM etc.)
    cost_per_1k_input_tokens: float = 0.0
    cost_per_1k_output_tokens: float = 0.0

    def api_key(self) -> Optional[str]:
        if not self.api_key_env:
            return None
        return os.environ.get(self.api_key_env)


class RoutingRule(BaseModel):
    name: str
    provider: str
    max_input_tokens: Optional[int] = None
    keywords: Optional[list[str]] = None


class CacheConfig(BaseModel):
    backend: str = "memory"
    ttl_seconds: int = 3600
    redis_url: Optional[str] = None


class GatewayConfig(BaseModel):
    providers: dict[str, ProviderConfig]
    routing: list[RoutingRule]
    fallback_chain: list[str] = []
    cache: CacheConfig = CacheConfig()
    cost_log_path: str = "./costs.jsonl"


def load_config(path: str | Path = "config.yaml") -> GatewayConfig:
    path = Path(path)
    if not path.exists():
        example = path.with_name("config.example.yaml")
        raise FileNotFoundError(
            f"{path} not found. Copy {example} to {path} and edit it first."
        )
    with open(path) as f:
        raw = yaml.safe_load(f)
    return GatewayConfig(**raw)
