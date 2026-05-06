import src.services.network_status_service as network_status_service
from src.services.network_status_service import NetworkStatusService


class _DummyConnection:
    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False


def test_probe_online_returns_standard_status_payload(monkeypatch) -> None:
    monkeypatch.setattr(
        network_status_service.socket,
        "create_connection",
        lambda *args, **kwargs: _DummyConnection(),
    )

    service = NetworkStatusService(host="1.1.1.1", port=53, timeout=0.8)
    result = service.probe()

    assert result["online"] is True
    assert result["checked_at"]
    assert result["probe_target"] == "1.1.1.1:53"
    assert result["latency_ms"] is not None
    assert "正常" in str(result["message"])


def test_probe_offline_returns_standard_status_payload(monkeypatch) -> None:
    def raise_offline(*args, **kwargs):
        raise OSError("offline")

    monkeypatch.setattr(network_status_service.socket, "create_connection", raise_offline)

    service = NetworkStatusService(host="1.1.1.1", port=53, timeout=0.8)
    result = service.probe()

    assert result["online"] is False
    assert result["checked_at"]
    assert result["probe_target"] == "1.1.1.1:53"
    assert result["latency_ms"] is None
    assert "未联网" in str(result["message"])
