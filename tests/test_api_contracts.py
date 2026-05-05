from fastapi.testclient import TestClient

from src.api.main import app


client = TestClient(app)


def test_translate_requires_source_declaration() -> None:
    response = client.post("/tasks/translate", json={"text": "hello"})

    assert response.status_code == 422


def test_glossary_export_endpoint_returns_200_and_format_for_valid_fmt() -> None:
    response = client.get("/glossary/export", params={"fmt": "csv"})

    assert response.status_code == 200
    payload = response.json()
    assert "format" in payload


def test_glossary_export_endpoint_returns_400_for_invalid_fmt() -> None:
    response = client.get("/glossary/export", params={"fmt": "pdf"})

    assert response.status_code == 400


def test_feedback_confirm_endpoint_missing_fields_returns_422() -> None:
    response = client.post("/feedback/confirm", json={})

    assert response.status_code == 422


def test_feedback_confirm_endpoint_valid_payload_returns_200() -> None:
    response = client.post(
        "/feedback/confirm",
        json={"task_id": "task-123", "confirmed": True},
    )

    assert response.status_code == 200


def test_task_events_endpoint_exists() -> None:
    response = client.get("/tasks/task-123/events")

    assert response.status_code == 200
    payload = response.json()
    assert "events" in payload
