from pathlib import Path
import json
import sys


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))


from consensus_translation.agent_acceptance import (
    acceptance_report_payload,
    format_acceptance_lines,
    main as acceptance_main,
    run_local_acceptance,
)


def test_run_local_acceptance_exercises_offline_desktop_agent_workflow(tmp_path):
    result = run_local_acceptance(tmp_path, project_id="acceptance-test")

    assert result.ok is True
    assert result.artifact_dir == tmp_path
    assert result.final_text.startswith("ZH:")
    assert result.verification["status"] == "passed"
    assert result.context["slice_count"] >= 3
    assert result.context["pending_slice_count"] >= 1
    assert "initial_translation" in result.task_types
    assert "continuation_translation" in result.task_types
    assert "stitch_and_verify" in result.task_types

    for path in result.artifacts.values():
        assert path.exists()

    manifest = json.loads(result.artifacts["manifest"].read_text(encoding="utf-8"))
    assert manifest["project_id"] == "acceptance-test"
    assert manifest["verification"]["status"] == "passed"


def test_format_acceptance_lines_is_suitable_for_desktop_review_panel(tmp_path):
    result = run_local_acceptance(tmp_path, project_id="acceptance-test")

    lines = format_acceptance_lines(result)

    assert lines[0].startswith("local acceptance: ok")
    assert any("verification: passed" in line for line in lines)
    assert any("artifact manifest:" in line for line in lines)
    assert any("tasks:" in line for line in lines)


def test_acceptance_report_payload_is_machine_readable(tmp_path):
    result = run_local_acceptance(tmp_path, project_id="acceptance-test")

    payload = acceptance_report_payload(result)

    assert payload["ok"] is True
    assert payload["verification"]["status"] == "passed"
    assert payload["context"]["pending_slice_count"] >= 1
    assert payload["artifacts"]["manifest"].endswith("acceptance-test.manifest.json")


def test_agent_acceptance_cli_writes_json_report(tmp_path):
    report_path = tmp_path / "acceptance-report.json"
    artifact_dir = tmp_path / "artifacts"

    exit_code = acceptance_main(
        [
            "--output-dir",
            str(artifact_dir),
            "--project-id",
            "cli-acceptance",
            "--report-json",
            str(report_path),
        ]
    )

    assert exit_code == 0
    assert report_path.exists()
    payload = json.loads(report_path.read_text(encoding="utf-8"))
    assert payload["ok"] is True
    assert payload["verification"]["status"] == "passed"
    assert Path(payload["artifacts"]["manifest"]).exists()
