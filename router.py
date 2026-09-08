from __future__ import annotations

from gateway.config import GatewayConfig, ProviderConfig


def count_tokens(messages: list[dict]) -> int:
    """Rough offline token estimate (~4 chars/token for English text).

    Deliberately avoids tiktoken here: exact encodings vary per model/vendor
    and downloading tokenizer files at startup makes a self-hosted gateway
    depend on an external network call it's meant to remove. Good enough for
    routing decisions; swap in a real tokenizer per-provider if you need
    exact counts for billing.
    """
    text = " ".join(m.get("content", "") for m in messages if isinstance(m.get("content"), str))
    return max(1, len(text) // 4)


def select_provider(
    config: GatewayConfig, messages: list[dict], requested_model: str
) -> ProviderConfig:
    """Return the ProviderConfig that should handle this request.

    If requested_model matches a configured provider name exactly, that
    provider is used directly (bypasses routing policy). Otherwise "auto"
    (or any unrecognized value) goes through the routing rules.
    """
    if requested_model in config.providers:
        return config.providers[requested_model]

    input_tokens = count_tokens(messages)
    full_text = " ".join(
        m.get("content", "") for m in messages if isinstance(m.get("content"), str)
    ).lower()

    for rule in config.routing:
        if rule.max_input_tokens is not None and input_tokens > rule.max_input_tokens:
            continue
        if rule.keywords and not any(kw.lower() in full_text for kw in rule.keywords):
            continue
        provider = config.providers.get(rule.provider)
        if provider:
            return provider

    # Should not happen if config has a catch-all "default" rule, but fail
    # safe by picking the first configured provider rather than crashing.
    return next(iter(config.providers.values()))


def fallback_providers(config: GatewayConfig) -> list[ProviderConfig]:
    return [config.providers[name] for name in config.fallback_chain if name in config.providers]
