from gateway.providers.base import ProviderError, ProviderResponse
from gateway.providers.openai_provider import call_openai
from gateway.providers.anthropic_provider import call_anthropic

__all__ = ["ProviderError", "ProviderResponse", "call_openai", "call_anthropic", "call_provider"]


async def call_provider(provider_config, messages: list[dict]) -> ProviderResponse:
    """Dispatch to the right adapter based on provider_config.kind."""
    if provider_config.kind == "openai":
        return await call_openai(provider_config, messages)
    if provider_config.kind == "anthropic":
        return await call_anthropic(provider_config, messages)
    raise ProviderError(f"Unknown provider kind: {provider_config.kind}")
