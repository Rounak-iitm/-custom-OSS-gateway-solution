"""OpenAI-compatible gateway: routes requests, caches responses, falls back
across providers, and logs cost/latency for every call.

Run with: uvicorn gateway.main:app --reload
"""
from __future__ import annotations

import time

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

from gateway.cache import build_cache, make_key
from gateway.config import GatewayConfig, ProviderConfig, load_config
from gateway.costs import log_request
from gateway.providers import ProviderError, call_provider
from gateway.router import count_tokens, fallback_providers, select_provider

app = FastAPI(title="llm-gateway")

_config: GatewayConfig = load_config()
_cache = build_cache(_config.cache)


class ChatRequest(BaseModel):
    model: str = "auto"
    messages: list[dict]


def _provider_name(config: GatewayConfig, provider: ProviderConfig) -> str:
    for name, p in config.providers.items():
        if p is provider:
            return name
    return provider.model


async def _try_provider(provider: ProviderConfig, messages: list[dict]):
    return await call_provider(provider, messages)


@app.post("/v1/chat/completions")
async def chat_completions(req: ChatRequest):
    primary = select_provider(_config, req.messages, req.model)
    primary_name = _provider_name(_config, primary)

    cache_key = make_key(req.messages, primary_name)
    cached = _cache.get(cache_key)
    if cached is not None:
        log_request(
            _config.cost_log_path, primary_name, primary,
            input_tokens=0, output_tokens=0, latency_ms=0, cache_hit=True,
        )
        return cached

    chain = [primary] + fallback_providers(_config)
    last_error: Exception | None = None

    for provider in chain:
        provider_name = _provider_name(_config, provider)
        start = time.perf_counter()
        try:
            result = await _try_provider(provider, req.messages)
        except ProviderError as e:
            last_error = e
            continue

        latency_ms = (time.perf_counter() - start) * 1000
        log_request(
            _config.cost_log_path, provider_name, provider,
            input_tokens=result.input_tokens, output_tokens=result.output_tokens,
            latency_ms=latency_ms, cache_hit=False,
        )

        response = {
            "id": "gw-" + cache_key[:12],
            "object": "chat.completion",
            "model": provider.model,
            "choices": [{"index": 0, "message": {"role": "assistant", "content": result.content}}],
            "usage": {
                "prompt_tokens": result.input_tokens,
                "completion_tokens": result.output_tokens,
                "total_tokens": result.input_tokens + result.output_tokens,
            },
            "_gateway": {"routed_to": provider_name, "cache_hit": False},
        }
        _cache.set(cache_key, response)
        return response

    raise HTTPException(status_code=502, detail=f"All providers failed. Last error: {last_error}")


@app.get("/healthz")
async def healthz():
    return {"status": "ok", "providers": list(_config.providers.keys())}
