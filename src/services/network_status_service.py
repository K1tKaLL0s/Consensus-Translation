import socket
import time
from datetime import UTC, datetime


class NetworkStatusService:
    def __init__(self, host: str = "1.1.1.1", port: int = 53, timeout: float = 0.8) -> None:
        self._host = host
        self._port = port
        self._timeout = timeout

    def probe(self) -> dict[str, object]:
        checked_at = datetime.now(UTC).isoformat()
        probe_target = f"{self._host}:{self._port}"
        started = time.perf_counter()

        try:
            with socket.create_connection((self._host, self._port), timeout=self._timeout):
                latency_ms = round((time.perf_counter() - started) * 1000, 2)
                return {
                    "online": True,
                    "checked_at": checked_at,
                    "probe_target": probe_target,
                    "latency_ms": latency_ms,
                    "message": "网络连接正常",
                }
        except OSError:
            return {
                "online": False,
                "checked_at": checked_at,
                "probe_target": probe_target,
                "latency_ms": None,
                "message": "当前未联网",
            }
