from fastapi.testclient import TestClient

from src.api.main import app


client = TestClient(app)


def test_file_task_rejects_unsupported_suffix() -> None:
    response = client.post(
        "/tasks/file",
        data={"usage": "translate", "source_declaration": "主题"},
        files={"file": ("sample.pdf", b"x", "application/pdf")},
    )

    assert response.status_code == 400


def test_translate_file_task_accepts_txt_and_provides_download() -> None:
    response = client.post(
        "/tasks/file",
        data={"usage": "translate", "source_declaration": "主题"},
        files={"file": ("sample.txt", "hello".encode("utf-8"), "text/plain")},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["usage"] == "translate"
    assert payload["download_ready"] is True

    task_id = payload["task_id"]
    task_response = client.get(f"/tasks/file/{task_id}")
    assert task_response.status_code == 200

    download_response = client.get(f"/downloads/{task_id}")
    assert download_response.status_code == 200


def test_glossary_file_task_returns_import_stats() -> None:
    response = client.post(
        "/tasks/file",
        data={"usage": "glossary", "source_declaration": "游戏王"},
        files={"file": ("terms.md", "术语A=訳語A".encode("utf-8"), "text/markdown")},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["usage"] == "glossary"
    assert payload["imported_count"] == 1
