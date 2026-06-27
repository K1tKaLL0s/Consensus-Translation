from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))


from consensus_translation.agent_providers import (
    MockCloudProvider,
    MockLocalModelProvider,
    OpenAICompatibleProvider,
    ProviderRequest,
)


class FakeResponse:
    def __init__(self, payload):
        self._payload = payload

    def raise_for_status(self):
        return None

    def json(self):
        return self._payload


def test_openai_compatible_provider_builds_chat_request_and_candidate():
    captured = {}

    def fake_post(url, headers, json, timeout):
        captured["url"] = url
        captured["headers"] = headers
        captured["json"] = json
        captured["timeout"] = timeout
        return FakeResponse(
            {
                "choices": [
                    {"message": {"content": "吾名利维坦。"}},
                ],
                "usage": {"total_tokens": 42},
            }
        )

    provider = OpenAICompatibleProvider(
        provider_id="deepseek-compatible",
        base_url="https://api.example.test/v1",
        model="example-translator",
        api_key="secret",
        estimated_cost=0.12,
        post_fn=fake_post,
    )

    candidate = provider.translate(
        ProviderRequest(
            text="我が名はレヴィアタン",
            source_lang="ja",
            target_lang="zh",
            topic="western_myth",
            round_index=1,
            conflict_points=["candidate_divergence"],
            training_text="我が名は竜王 -> 吾名龙王",
        )
    )

    assert provider.requires_api is True
    assert captured["url"] == "https://api.example.test/v1/chat/completions"
    assert captured["headers"]["Authorization"] == "Bearer secret"
    assert captured["json"]["model"] == "example-translator"
    assert "ja->zh" in captured["json"]["messages"][0]["content"]
    assert "western_myth" in captured["json"]["messages"][0]["content"]
    assert "candidate_divergence" in captured["json"]["messages"][0]["content"]
    assert "我が名は竜王 -> 吾名龙王" in captured["json"]["messages"][0]["content"]
    assert candidate.provider_id == "deepseek-compatible"
    assert candidate.text == "吾名利维坦。"
    assert candidate.confidence == 0.5
    assert candidate.cost == 0.12
    assert candidate.term_hits == {"total_tokens": 42}

def test_mock_local_providers_are_explicitly_labeled_and_independent():
    provider_a = MockLocalModelProvider(
        provider_id="mockLocalProviderA",
        provider_role="local_a",
        prefix="A:",
        confidence=0.61,
    )
    provider_b = MockLocalModelProvider(
        provider_id="mockLocalProviderB",
        provider_role="local_b",
        prefix="B:",
        confidence=0.59,
    )
    request = ProviderRequest(
        text="Leviathan",
        source_lang="en",
        target_lang="zh",
        topic="myth",
        round_index=1,
    )

    candidate_a = provider_a.translate(request)
    candidate_b = provider_b.translate(request)

    assert candidate_a.provider_id == "mockLocalProviderA"
    assert candidate_b.provider_id == "mockLocalProviderB"
    assert candidate_a.text == "A:Leviathan"
    assert candidate_b.text == "B:Leviathan"
    assert candidate_a.provider_kind == "local"
    assert candidate_b.provider_kind == "local"
    assert candidate_a.provider_role == "local_a"
    assert candidate_b.provider_role == "local_b"
    assert candidate_a.is_mock is True
    assert candidate_b.is_mock is True
    assert "mock-provider" in candidate_a.warnings
    assert "mock-provider" in candidate_b.warnings


def test_mock_cloud_provider_is_limited_to_workflow_simulation():
    provider = MockCloudProvider(provider_id="mockCloudProvider", confidence=0.7)

    candidate = provider.translate(
        ProviderRequest(
            text="Leviathan",
            source_lang="en",
            target_lang="zh",
            topic="myth",
            round_index=2,
            conflict_points=["candidate_divergence"],
        )
    )

    assert provider.requires_api is False
    assert candidate.provider_kind == "cloud"
    assert candidate.provider_role == "cloud"
    assert candidate.is_mock is True
    assert "round=2" in candidate.reasoning
    assert "candidate_divergence" in candidate.reasoning
    assert "mock-provider" in candidate.warnings
