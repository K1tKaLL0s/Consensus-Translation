from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))


from consensus_translation.agent_credentials import LocalCredentialStore
from consensus_translation.agent_provider_config import (
    ProviderConfig,
    build_enabled_providers,
)
from consensus_translation.agent_providers import OpenAICompatibleProvider
from consensus_translation.agent_store import AgentRunStore
from consensus_translation.desktop_agent_app import DesktopAgentController
from consensus_translation.desktop_agent_app import default_desktop_credentials_path


def test_sqlite_store_persists_provider_configs_without_plaintext_secret(tmp_path):
    store = AgentRunStore(tmp_path / "agent.sqlite3")
    config = ProviderConfig(
        provider_id="openai-main",
        kind="openai_compatible",
        base_url="https://api.example.test/v1",
        model="translator",
        credential_id="openai-main-key",
        estimated_cost=0.25,
        enabled=True,
    )

    store.upsert_provider_config(config)

    assert store.list_provider_configs() == [config]
    assert store.list_provider_configs(enabled=True) == [config]
    assert store.list_provider_configs(enabled=False) == []
    assert b"secret-value" not in (tmp_path / "agent.sqlite3").read_bytes()


def test_sqlite_store_can_disable_provider_config(tmp_path):
    store = AgentRunStore(tmp_path / "agent.sqlite3")
    config = ProviderConfig(
        provider_id="remote-disabled",
        kind="openai_compatible",
        base_url="https://api.example.test/v1",
        model="translator",
        credential_id="remote-disabled-key",
        estimated_cost=0.5,
        enabled=False,
    )

    store.upsert_provider_config(config)

    assert store.list_provider_configs() == [config]
    assert store.list_provider_configs(enabled=True) == []
    assert store.list_provider_configs(enabled=False) == [config]


def test_build_enabled_providers_uses_only_enabled_configs_and_local_credentials(tmp_path):
    credentials = LocalCredentialStore(tmp_path / "credentials.json")
    credentials.set_secret("enabled-key", "api-key")
    enabled = ProviderConfig(
        provider_id="enabled-remote",
        kind="openai_compatible",
        base_url="https://api.example.test/v1",
        model="translator",
        credential_id="enabled-key",
        estimated_cost=0.25,
        enabled=True,
    )
    disabled = ProviderConfig(
        provider_id="disabled-remote",
        kind="openai_compatible",
        base_url="https://api.example.test/v1",
        model="translator",
        credential_id="missing-disabled-key",
        estimated_cost=0.25,
        enabled=False,
    )

    providers = build_enabled_providers([enabled, disabled], credentials)

    assert len(providers) == 1
    assert isinstance(providers[0], OpenAICompatibleProvider)
    assert providers[0].provider_id == "enabled-remote"


def test_desktop_controller_loads_enabled_provider_configs_from_store(tmp_path):
    store = AgentRunStore(tmp_path / "agent.sqlite3")
    credentials = LocalCredentialStore(tmp_path / "credentials.json")
    credentials.set_secret("remote-key", "api-key")
    store.upsert_provider_config(
        ProviderConfig(
            provider_id="remote-a",
            kind="openai_compatible",
            base_url="https://api.example.test/v1",
            model="translator",
            credential_id="remote-key",
            estimated_cost=0.25,
            enabled=True,
        )
    )
    controller = DesktopAgentController(store=store)

    providers = controller.load_enabled_provider_configs(credentials)

    assert [provider.provider_id for provider in providers] == ["remote-a"]
    assert [provider.provider_id for provider in controller.providers] == ["remote-a"]


def test_default_desktop_credentials_path_uses_local_app_data(monkeypatch, tmp_path):
    monkeypatch.setenv("LOCALAPPDATA", str(tmp_path))

    path = default_desktop_credentials_path()

    assert path == tmp_path / "ConsensusTranslation" / "credentials.json"


def test_desktop_controller_saves_provider_settings_and_secret_without_plaintext(tmp_path):
    store = AgentRunStore(tmp_path / "agent.sqlite3")
    credentials = LocalCredentialStore(tmp_path / "credentials.json")
    controller = DesktopAgentController(store=store)

    config = controller.save_provider_settings(
        credential_store=credentials,
        provider_id="remote-a",
        base_url="https://api.example.test/v1",
        model="translator",
        api_key="secret-api-key",
        estimated_cost=0.25,
        enabled=True,
    )

    assert config == ProviderConfig(
        provider_id="remote-a",
        kind="openai_compatible",
        base_url="https://api.example.test/v1",
        model="translator",
        credential_id="remote-a-key",
        estimated_cost=0.25,
        enabled=True,
    )
    assert store.list_provider_configs(enabled=True) == [config]
    assert credentials.get_secret("remote-a-key") == "secret-api-key"
    assert b"secret-api-key" not in (tmp_path / "agent.sqlite3").read_bytes()
    assert "secret-api-key" not in (tmp_path / "credentials.json").read_text(encoding="utf-8")

    providers = controller.load_enabled_provider_configs(credentials)

    assert len(providers) == 1
    assert isinstance(providers[0], OpenAICompatibleProvider)
    assert providers[0].provider_id == "remote-a"
