from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))


from consensus_translation.agent_contracts import TranslationCandidate
from consensus_translation.agent_provider_smoke import (
    ProviderSmokeResult,
    format_provider_smoke_lines,
    smoke_test_provider,
)
from consensus_translation.agent_providers import ProviderRequest


class CapturingProvider:
    provider_id = "remote-a"
    requires_api = True
    estimated_cost = 0.25

    def __init__(self) -> None:
        self.request: ProviderRequest | None = None

    def translate(self, request: ProviderRequest) -> TranslationCandidate:
        self.request = request
        return TranslationCandidate(
            provider_id=self.provider_id,
            text="translated smoke",
            confidence=0.5,
            cost=self.estimated_cost,
            term_hits={"total_tokens": 7},
            warnings=["low-confidence"],
        )


class FailingProvider:
    provider_id = "remote-failing"
    requires_api = True
    estimated_cost = 0.5

    def translate(self, request: ProviderRequest) -> TranslationCandidate:
        raise RuntimeError("endpoint unavailable")


def test_smoke_test_provider_uses_small_translation_request_and_returns_result():
    provider = CapturingProvider()

    result = smoke_test_provider(
        provider,
        source_lang="en",
        target_lang="zh",
        topic="provider-smoke",
        sample_text="Leviathan",
        allow_live_remote=True,
    )

    assert isinstance(result, ProviderSmokeResult)
    assert result.ok is True
    assert result.provider_id == "remote-a"
    assert result.sample_text == "Leviathan"
    assert result.translated_text == "translated smoke"
    assert result.cost == 0.25
    assert result.total_tokens == 7
    assert result.warnings == ["low-confidence"]
    assert result.error is None
    assert result.latency_ms >= 0
    assert provider.request == ProviderRequest(
        text="Leviathan",
        source_lang="en",
        target_lang="zh",
        topic="provider-smoke",
        round_index=1,
    )


def test_smoke_test_provider_reports_errors_without_raising():
    result = smoke_test_provider(FailingProvider(), allow_live_remote=True)

    assert result.ok is False
    assert result.provider_id == "remote-failing"
    assert result.translated_text == ""
    assert result.cost == 0.0
    assert result.total_tokens == 0
    assert result.error == "endpoint unavailable"


def test_smoke_test_provider_skips_remote_provider_when_api_disabled():
    provider = CapturingProvider()

    result = smoke_test_provider(provider, api_enabled=False)

    assert result.ok is False
    assert result.provider_id == "remote-a"
    assert result.error == "api disabled"
    assert provider.request is None


def test_smoke_test_provider_blocks_remote_provider_without_confirmation():
    provider = CapturingProvider()

    result = smoke_test_provider(provider, api_enabled=True)

    assert result.ok is False
    assert result.error == "live remote smoke requires explicit confirmation"
    assert provider.request is None


def test_format_provider_smoke_lines_summarizes_success_and_failure():
    lines = format_provider_smoke_lines(
        [
            ProviderSmokeResult(
                provider_id="remote-a",
                ok=True,
                sample_text="Leviathan",
                translated_text="translated smoke",
                latency_ms=12,
                cost=0.25,
                total_tokens=7,
                warnings=[],
                error=None,
            ),
            ProviderSmokeResult(
                provider_id="remote-b",
                ok=False,
                sample_text="Leviathan",
                translated_text="",
                latency_ms=3,
                cost=0.0,
                total_tokens=0,
                warnings=[],
                error="endpoint unavailable",
            ),
        ]
    )

    assert lines == [
        "provider smoke: 2 checked | ok=1 | failed=1",
        "OK remote-a | latency=12ms | tokens=7 | cost=0.25 | translated smoke",
        "FAIL remote-b | latency=3ms | endpoint unavailable",
    ]
