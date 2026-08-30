from __future__ import annotations

import httpx

from gateway.config import ProviderConfig
from gateway.providers.base import ProviderError, ProviderResponse

_BASE_URL = "https://api.anthropic.com/v1/messages"
_ANTHROPIC_VERSION = "2023-06-01"


async def call_anthropic(provider: ProviderConfig, messages: list[dict]) -> ProviderResponse:
    api_key = provider.api_key()
    if not api_key:
        raise ProviderError(f"Missing API key (env: {provider.api_key_env}) for anthropic provider")

    # Anthropic separates a top-level "system" message from the turn history.
    system = "\n".join(m["content"] for m in messages if m.get("role") == "system")
    turns = [m for m in messages if m.get("role") != "system"]

    url = provider.base_url or _BASE_URL
    body = {
        "model": provider.model,
        "max_tokens": 1024,
        "messages": turns,
    }
    if system:
        body["system"] = system

    async with httpx.AsyncClient(timeout=60) as client:
        try:
            resp = await client.post(
                url,
                headers={
                    "x-api-key": api_key,
                    "anthropic-version": _ANTHROPIC_VERSION,
                    "content-type": "application/json",
                },
                json=body,
            )
            resp.raise_for_status()
        except httpx.HTTPStatusError as e:
            raise ProviderError(f"Anthropic error {e.response.status_code}: {e.response.text}") from e
        except httpx.RequestError as e:
            raise ProviderError(f"Anthropic request failed: {e}") from e

    data = resp.json()
    content = "".join(block.get("text", "") for block in data.get("content", []))
    usage = data.get("usage", {})
    return ProviderResponse(
        content=content,
        input_tokens=usage.get("input_tokens", 0),
        output_tokens=usage.get("output_tokens", 0),
        raw=data,
    )
