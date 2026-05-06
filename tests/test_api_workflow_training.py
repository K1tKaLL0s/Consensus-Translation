from pathlib import Path

import src.api.main as api_main
from fastapi.testclient import TestClient
import pytest

from src.services.workflow_service import WorkflowService


@pytest.fixture(autouse=True)
def _reset_workflow_service(tmp_path: Path) -> None:
    reference_dir = tmp_path / "references"
    reference_dir.mkdir(parents=True, exist_ok=True)
    api_main._WORKFLOW_SERVICE = WorkflowService(reference_dir=reference_dir)


client = TestClient(api_main.app)


def test_training_workflow_happy_path_with_uploaded_reference() -> None:
    start_response = client.post(
        "/workflow/training/start",
        data={"source_declaration": "主题"},
        files={
            "raw_file": ("raw.txt", "raw training text".encode("utf-8"), "text/plain"),
            "reference_file": (
                "reference.txt",
                "reference training text".encode("utf-8"),
                "text/plain",
            ),
        },
    )

    assert start_response.status_code == 200
    started = start_response.json()
    assert started["status"] == "training_started"
    assert started["reconciled"] is False
    assert started["committed"] is False
    workflow_id = started["workflow_id"]

    reconcile_response = client.post(
        "/workflow/training/reconcile",
        json={"workflow_id": workflow_id},
    )
    assert reconcile_response.status_code == 200
    reconciled = reconcile_response.json()
    assert reconciled["status"] == "training_reconciled"
    assert reconciled["reconciled"] is True
    assert reconciled["committed"] is False

    commit_response = client.post(
        "/workflow/training/commit",
        json={"workflow_id": workflow_id},
    )
    assert commit_response.status_code == 200
    committed = commit_response.json()
    assert committed["status"] == "training_committed"
    assert committed["reconciled"] is True
    assert committed["committed"] is True
    assert committed["commit_count"] == 1

    get_response = client.get(f"/workflow/training/{workflow_id}")
    assert get_response.status_code == 200
    current = get_response.json()
    assert current["status"] == "training_committed"
    assert current["reconciled"] is True
    assert current["committed"] is True


def test_training_workflow_start_rejects_blank_source_declaration() -> None:
    response = client.post(
        "/workflow/training/start",
        data={"source_declaration": "   "},
        files={"raw_file": ("raw.txt", "hello".encode("utf-8"), "text/plain")},
    )

    assert response.status_code == 400


def test_training_workflow_unknown_ids_return_404() -> None:
    reconcile_response = client.post(
        "/workflow/training/reconcile",
        json={"workflow_id": "missing-id"},
    )
    assert reconcile_response.status_code == 404

    commit_response = client.post(
        "/workflow/training/commit",
        json={"workflow_id": "missing-id"},
    )
    assert commit_response.status_code == 404

    get_response = client.get("/workflow/training/missing-id")
    assert get_response.status_code == 404


def test_training_workflow_start_rejects_non_utf8_upload() -> None:
    response = client.post(
        "/workflow/training/start",
        data={"source_declaration": "主题"},
        files={"raw_file": ("raw.txt", b"\xff\xfe\xfa", "text/plain")},
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "uploaded file must be valid UTF-8 text"


def test_training_workflow_commit_before_reconcile_returns_409() -> None:
    start_response = client.post(
        "/workflow/training/start",
        data={"source_declaration": "主题"},
        files={
            "raw_file": ("raw.txt", "raw training text".encode("utf-8"), "text/plain"),
            "reference_file": (
                "reference.txt",
                "reference training text".encode("utf-8"),
                "text/plain",
            ),
        },
    )

    assert start_response.status_code == 200
    workflow_id = start_response.json()["workflow_id"]

    commit_response = client.post(
        "/workflow/training/commit",
        json={"workflow_id": workflow_id},
    )

    assert commit_response.status_code == 409
    assert commit_response.json()["detail"] == "training workflow must be reconciled before commit"


def test_training_workflow_start_uses_fallback_reference_file_when_omitted(tmp_path: Path) -> None:
    reference_path = tmp_path / "references" / "yu_gi_oh.txt"
    reference_path.write_text("fallback reference text", encoding="utf-8")

    response = client.post(
        "/workflow/training/start",
        data={"source_declaration": "yu_gi_oh"},
        files={"raw_file": ("raw.txt", "raw training text".encode("utf-8"), "text/plain")},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["reference_text"] == "fallback reference text"
    assert payload["reference_path"] == str(reference_path)


def test_training_workflow_start_without_reference_file_or_fallback_returns_400() -> None:
    response = client.post(
        "/workflow/training/start",
        data={"source_declaration": "missing_source"},
        files={"raw_file": ("raw.txt", "raw training text".encode("utf-8"), "text/plain")},
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "reference text is required"
