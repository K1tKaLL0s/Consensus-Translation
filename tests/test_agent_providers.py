from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))


from consensus_translation.agent_providers import (
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
