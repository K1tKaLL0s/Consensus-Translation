from pathlib import Path
import json
import sys


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))


from consensus_translation.agent_artifacts import export_translation_artifacts
from consensus_translation.agent_context import ContextBudget
from consensus_translation.agent_contracts import AgentMode
from consensus_translation.agent_continuation import run_context_managed_translation
from consensus_translation.agent_providers import EchoModelProvider


def test_export_translation_artifacts_writes_delivery_and_audit_files(tmp_path):
    result = run_context_managed_translation(
        text="alpha beta\n\ngamma delta\n\nomega zeta",
        source_lang="en",
        target_lang="zh",
        topic="general",
        mode=AgentMode.LEARNING,
        providers=[EchoModelProvider("echo-local", prefix="ZH:")],
        context_budget=ContextBudget(max_context_tokens=7, reserved_output_tokens=2),
        api_enabled=False,
        budget_limit=0.0,
        allow_mock_providers=True,
    )

    artifacts = export_translation_artifacts(
        result,
        output_dir=tmp_path,
        base_name="chapter01",
    )

    assert set(artifacts) == {
        "final_text",
        "translation_brief",
        "verification",
        "segments",
        "manifest",
    }
    assert artifacts["final_text"].name == "chapter01.translation.txt"
    assert artifacts["final_text"].read_text(encoding="utf-8") == result.final_text
    assert "写作结构" in artifacts["translation_brief"].read_text(encoding="utf-8")

    verification = json.loads(artifacts["verification"].read_text(encoding="utf-8"))
    assert verification["status"] == "passed"
    assert verification["source_task_ids"] == result.stitch_task.source_task_ids

    segments = json.loads(artifacts["segments"].read_text(encoding="utf-8"))
    assert [segment["task_type"] for segment in segments] == [
        "initial_translation",
        "continuation_translation",
        "stitch_and_verify",
    ]
    assert segments[-1]["verification"]["status"] == "passed"

    manifest = json.loads(artifacts["manifest"].read_text(encoding="utf-8"))
    assert manifest["artifact_version"] == "desktop-agent-artifacts-v1"
    assert manifest["files"]["final_text"] == "chapter01.translation.txt"
    assert manifest["context"]["slice_count"] == 3
    assert manifest["context"]["pending_slice_count"] == 1
    assert manifest["verification"]["status"] == "passed"
