from fastapi.testclient import TestClient

from src.api.main import app


client = TestClient(app)


def test_translate_requires_source_declaration() -> None:
    response = client.post("/tasks/translate", json={"text": "hello"})

    assert response.status_code == 422


def test_glossary_export_endpoint_returns_200_or_400() -> None:
    response = client.get("/glossary/export", params={"fmt": "csv"})

    assert response.status_code in {200, 400}


def test_feedback_confirm_endpoint_exists() -> None:
    response = client.post("/feedback/confirm")

    assert response.status_code in {200, 422}


def test_task_events_endpoint_exists() -> None:
    response = client.get("/tasks/task-123/events")

    assert response.status_code == 200
