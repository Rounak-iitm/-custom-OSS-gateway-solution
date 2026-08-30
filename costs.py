"""Append-only cost/latency log, one JSON line per request.

Swap `log_request` for a real sink (Postgres, Prometheus, etc.) later —
callers don't need to change.
"""
from __future__ import annotations

import json
import time
from pathlib import Path

from gateway.config import ProviderConfig


def estimate_cost(provider: ProviderConfig, input_tokens: int, output_tokens: int) -> float:
    return (
        input_tokens / 1000 * provider.cost_per_1k_input_tokens
        + output_tokens / 1000 * provider.cost_per_1k_output_tokens
    )


def log_request(
    log_path: str,
    provider_name: str,
    provider: ProviderConfig,
    input_tokens: int,
    output_tokens: int,
    latency_ms: float,
    cache_hit: bool,
) -> None:
    record = {
        "ts": time.time(),
        "provider": provider_name,
        "model": provider.model,
        "input_tokens": input_tokens,
        "output_tokens": output_tokens,
        "estimated_cost_usd": 0.0 if cache_hit else estimate_cost(provider, input_tokens, output_tokens),
        "latency_ms": latency_ms,
        "cache_hit": cache_hit,
    }
    path = Path(log_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "a") as f:
        f.write(json.dumps(record) + "\n")
