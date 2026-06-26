from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))


from consensus_translation.agent_credentials import LocalCredentialStore
from consensus_translation.agent_provider_config import ProviderConfig, build_provider
from consensus_translation.agent_providers import OpenAICompatibleProvider


def test_local_credential_store_keeps_secret_out_of_plaintext_file(tmp_path):
    store = LocalCredentialStore(tmp_path / "credentials.json")
    store.set_secret("deepseek", "secret-value")

    raw = (tmp_path / "credentials.json").read_text(encoding="utf-8")

    assert "secret-value" not in raw
    assert store.get_secret("deepseek") == "secret-value"


def test_provider_config_builds_openai_compatible_provider_from_credential_store(tmp_path):
    store = LocalCredentialStore(tmp_path / "credentials.json")
    store.set_secret("openai-main", "api-key")
    config = ProviderConfig(
        provider_id="openai-main",
        kind="openai_compatible",
        base_url="https://api.example.test/v1",
        model="translator",
        credential_id="openai-main",
        estimated_cost=0.25,
    )

    provider = build_provider(config, credential_store=store)

    assert isinstance(provider, OpenAICompatibleProvider)
    assert provider.provider_id == "openai-main"
    assert provider.estimated_cost == 0.25
    assert "api-key" not in repr(config)
