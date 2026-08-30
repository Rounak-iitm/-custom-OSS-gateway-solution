from __future__ import annotations

import httpx

from gateway.config import ProviderConfig
from gateway.providers.base import ProviderError, ProviderResponse

_BASE_URL = "https://api.openai.com/v1/chat/completions"


async def call_openai(provider: ProviderConfig, messages: list[dict]) -> ProviderResponse:
    api_key = provider.api_key()
    if not api_key:
        raise ProviderError(f"Missing API key (env: {provider.api_key_env}) for openai provider")

    url = provider.base_url or _BASE_URL
    async with httpx.AsyncClient(timeout=60) as client:
        try:
            resp = await client.post(
                url,
                headers={"Authorization": f"Bearer {api_key}"},
                json={"model": provider.model, "messages": messages},
            )
            resp.raise_for_status()
        except httpx.HTTPStatusError as e:
            raise ProviderError(f"OpenAI error {e.response.status_code}: {e.response.text}") from e
        except httpx.RequestError as e:
            raise ProviderError(f"OpenAI request failed: {e}") from e

    data = resp.json()
    choice = data["choices"][0]["message"]["content"]
    usage = data.get("usage", {})
    return ProviderResponse(
        content=choice,
        input_tokens=usage.get("prompt_tokens", 0),
        output_tokens=usage.get("completion_tokens", 0),
        raw=data,
    )
