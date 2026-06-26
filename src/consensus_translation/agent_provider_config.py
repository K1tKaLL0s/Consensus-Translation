from __future__ import annotations

from dataclasses import dataclass

from consensus_translation.agent_credentials import LocalCredentialStore
from consensus_translation.agent_providers import OpenAICompatibleProvider


@dataclass(frozen=True)
class ProviderConfig:
    provider_id: str
    kind: str
    base_url: str
    model: str
    credential_id: str
    estimated_cost: float = 0.0
    enabled: bool = True


def build_provider(config: ProviderConfig, credential_store: LocalCredentialStore):
    if config.kind != "openai_compatible":
        raise ValueError(f"unsupported provider kind: {config.kind}")
    return OpenAICompatibleProvider(
        provider_id=config.provider_id,
        base_url=config.base_url,
        model=config.model,
        api_key=credential_store.get_secret(config.credential_id),
        estimated_cost=config.estimated_cost,
    )


def build_enabled_providers(
    configs: list[ProviderConfig],
    credential_store: LocalCredentialStore,
):
    return [
        build_provider(config, credential_store)
        for config in configs
        if config.enabled
    ]
