from pathlib import Path

import pytest

from src.services.workflow_service import WorkflowService


def test_translate_confirm_is_idempotent_for_glossary_write_count() -> None:
    service = WorkflowService(reference_dir=Path("references"))
    workflow = service.start_translate(
        source_declaration="game_terms",
        filename="chapter1.txt",
        text="initial translation",
    )
    workflow_id = str(workflow["workflow_id"])

    first_confirm = service.confirm_translate(workflow_id=workflow_id, confirmed=True)
    second_confirm = service.confirm_translate(workflow_id=workflow_id, confirmed=True)
    current = service.get_translate(workflow_id)

    assert first_confirm["confirmed"] is True
    assert second_confirm["confirmed"] is True
    assert current["glossary_write_count"] == 1


def test_start_training_falls_back_to_reference_file_when_reference_text_missing(
    tmp_path: Path,
) -> None:
    reference_dir = tmp_path / "reference"
    reference_dir.mkdir()
    (reference_dir / "yu_gi_oh.txt").write_text("fallback reference text", encoding="utf-8")

    service = WorkflowService(reference_dir=reference_dir)

    training = service.start_training(
        source_declaration="yu_gi_oh",
        raw_filename="input.txt",
        raw_text="raw content",
        reference_text=None,
    )

    assert training["reference_text"] == "fallback reference text"
    assert training["reference_path"] == str(reference_dir / "yu_gi_oh.txt")


def test_start_training_raises_when_fallback_reference_file_missing(tmp_path: Path) -> None:
    service = WorkflowService(reference_dir=tmp_path / "reference")

    with pytest.raises(ValueError, match="reference text is required"):
        service.start_training(
            source_declaration="missing_source",
            raw_filename="input.txt",
            raw_text="raw content",
            reference_text=None,
        )
