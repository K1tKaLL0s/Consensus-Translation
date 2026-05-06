from fastapi.testclient import TestClient

from src.api.main import app


client = TestClient(app)


def test_system_network_endpoint_returns_200_and_required_keys() -> None:
    response = client.get("/system/network")

    assert response.status_code == 200
    payload = response.json()
    assert "online" in payload
    assert "checked_at" in payload
    assert "probe_target" in payload
    assert "message" in payload
