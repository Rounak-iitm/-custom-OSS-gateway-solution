from __future__ import annotations

from dataclasses import dataclass


@dataclass
class ProviderResponse:
    content: str
    input_tokens: int
    output_tokens: int
    raw: dict


class ProviderError(Exception):
    """Raised when a provider call fails (auth, rate limit, network, etc.).
    The gateway catches this to trigger fallback_chain.
    """
