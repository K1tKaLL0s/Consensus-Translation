import os
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))


from consensus_translation.agent_evaluators import (
    CometTranslationEvaluator,
    DeterministicTranslationEvaluator,
    EvaluationRequest,
    ExternalCometTranslationEvaluator,
    OpenAICompatibleJudgeEvaluator,
)


class FakeResponse:
    def __init__(self, payload):
        self._payload = payload

    def raise_for_status(self):
        return None

    def json(self):
        return self._payload


def test_deterministic_evaluator_wraps_existing_metrics():
    evaluator = DeterministicTranslationEvaluator()

    result = evaluator.evaluate(
        EvaluationRequest(
            source_text="hello",
            candidate_text="gold target",
            reference_text="gold target",
            source_lang="en",
            target_lang="zh",
            topic="general",
            round_index=1,
        )
    )

    assert result.evaluator_id == "deterministic"
    assert result.score == 1.0
    assert result.metrics["overall"] == 1.0
    assert result.requires_human_review is False


def test_openai_compatible_judge_evaluator_parses_json_score_and_rationale():
    captured = {}

    def fake_post(url, headers, json, timeout):
        captured["url"] = url
        captured["headers"] = headers
        captured["json"] = json
        captured["timeout"] = timeout
        return FakeResponse(
            {
                "choices": [
                    {
                        "message": {
                            "content": '{"score": 0.82, "rationale": "terms consistent"}'
                        }
                    }
                ],
                "usage": {"total_tokens": 31},
            }
        )

    evaluator = OpenAICompatibleJudgeEvaluator(
        evaluator_id="llm-judge",
        base_url="https://api.example.test/v1",
        model="judge-model",
        api_key="secret",
        estimated_cost=0.17,
        post_fn=fake_post,
    )

    result = evaluator.evaluate(
        EvaluationRequest(
            source_text="source",
            candidate_text="candidate",
            reference_text="reference",
            source_lang="en",
            target_lang="zh",
            topic="general",
            round_index=2,
        )
    )

    assert captured["url"] == "https://api.example.test/v1/chat/completions"
    assert captured["headers"]["Authorization"] == "Bearer secret"
    assert captured["json"]["model"] == "judge-model"
    assert "score" in captured["json"]["messages"][0]["content"]
    assert result.evaluator_id == "llm-judge"
    assert result.score == 0.82
    assert result.metrics == {"llm_score": 0.82, "total_tokens": 31.0}
    assert result.rationale == "terms consistent"


def test_comet_evaluator_uses_injected_predictor_without_importing_heavy_runtime():
    captured = {}

    class FakeCometModel:
        def predict(self, data, batch_size, gpus):
            captured["data"] = data
            captured["batch_size"] = batch_size
            captured["gpus"] = gpus
            return {"scores": [0.73]}

    evaluator = CometTranslationEvaluator(
        model=FakeCometModel(),
        evaluator_id="comet-fake",
    )

    result = evaluator.evaluate(
        EvaluationRequest(
            source_text="source",
            candidate_text="candidate",
            reference_text="reference",
            source_lang="en",
            target_lang="zh",
            topic="general",
            round_index=1,
        )
    )

    assert captured["data"] == [
        {"src": "source", "mt": "candidate", "ref": "reference"}
    ]
    assert result.evaluator_id == "comet-fake"
    assert result.score == 0.73
    assert result.metrics == {"comet_score": 0.73}


def test_external_comet_evaluator_calls_sidecar_and_parses_json(tmp_path):
    captured = {}

    def fake_runner(command, timeout):
        captured["command"] = command
        captured["timeout"] = timeout
        source_path = Path(command[command.index("-s") + 1])
        captured["source_text"] = source_path.read_text(encoding="utf-8")
        output_path = Path(command[command.index("--to_json") + 1])
        output_path.write_text(
            '{"candidate.txt": [{"src": "source", "mt": "candidate", '
            '"ref": "reference", "COMET": 0.81}]}',
            encoding="utf-8",
        )

        class Result:
            returncode = 0
            stdout = "Predictions saved"
            stderr = ""

        return Result()

    evaluator = ExternalCometTranslationEvaluator(
        command=str(tmp_path / "comet-score.exe"),
        model_name="Unbabel/wmt22-comet-da",
        model_storage_path=tmp_path / "models",
        runner=fake_runner,
    )

    result = evaluator.evaluate(
        EvaluationRequest(
            source_text="source\nline",
            candidate_text="candidate\nline",
            reference_text="reference\nline",
            source_lang="en",
            target_lang="zh",
            topic="general",
            round_index=1,
        )
    )

    command = captured["command"]
    assert command[0] == str(tmp_path / "comet-score.exe")
    assert command[command.index("--gpus") + 1] == "0"
    assert command[command.index("--model") + 1] == "Unbabel/wmt22-comet-da"
    assert command[command.index("--model_storage_path") + 1] == str(
        tmp_path / "models"
    )
    assert captured["source_text"] == "source line\n"
    assert result.score == 0.81
    assert result.metrics == {"comet_score": 0.81}


def test_external_comet_evaluator_sets_cache_environment(tmp_path, monkeypatch):
    monkeypatch.setenv("HF_HOME", str(tmp_path / "previous-hf"))
    captured = {}

    def fake_runner(command, timeout):
        captured["hf_home"] = os.environ.get("HF_HOME")
        captured["hub_cache"] = os.environ.get("HUGGINGFACE_HUB_CACHE")
        captured["transformers_cache"] = os.environ.get("TRANSFORMERS_CACHE")
        captured["torch_home"] = os.environ.get("TORCH_HOME")
        captured["xet_disabled"] = os.environ.get("HF_HUB_DISABLE_XET")
        output_path = Path(command[command.index("--to_json") + 1])
        output_path.write_text(
            '{"candidate.txt": [{"COMET": 0.82}]}',
            encoding="utf-8",
        )

        class Result:
            returncode = 0
            stdout = "Predictions saved"
            stderr = ""

        return Result()

    model_cache = tmp_path / "models"
    evaluator = ExternalCometTranslationEvaluator(
        model_storage_path=model_cache,
        runner=fake_runner,
    )

    result = evaluator.evaluate(
        EvaluationRequest(
            source_text="source",
            candidate_text="candidate",
            reference_text="reference",
            source_lang="en",
            target_lang="zh",
            topic="general",
            round_index=1,
        )
    )

    assert captured["hf_home"] == str(model_cache / "huggingface")
    assert captured["hub_cache"] == str(model_cache / "huggingface" / "hub")
    assert captured["transformers_cache"] == str(model_cache / "huggingface" / "hub")
    assert captured["torch_home"] == str(model_cache / "torch")
    assert captured["xet_disabled"] == "1"
    assert os.environ["HF_HOME"] == str(tmp_path / "previous-hf")
    assert result.score == 0.82
