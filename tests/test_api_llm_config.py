from fastapi.testclient import TestClient

from src.api.main import app


client = TestClient(app)


def test_llm_config_crud() -> None:
    save = client.post(
        "/config/llm",
        json={"provider": "gemini", "model": "gemini-2.5-pro", "api_key": "x"},
    )
    assert save.status_code == 200
    saved_payload = save.json()
    assert saved_payload["provider"] == "gemini"
    assert saved_payload["api_key_configured"] is True

    status = client.get("/config/llm")
    assert status.status_code == 200
    payload = status.json()
    assert payload["provider"] == "gemini"
    assert payload["api_key_configured"] is True

    deleted = client.delete("/config/llm")
    assert deleted.status_code == 200
    deleted_payload = deleted.json()
    assert deleted_payload["provider"] is None
    assert deleted_payload["api_key_configured"] is False
