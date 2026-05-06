from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any


_ALLOWED_LEVELS = {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"}


def resolve_minimum_log_level() -> str:
    raw = os.getenv("CT_MIN_LOG_LEVEL", "INFO")
    normalized = raw.strip().upper() if raw else "INFO"
    if normalized in _ALLOWED_LEVELS:
        return normalized
    return "INFO"


def export_audit_payload(payload: dict[str, Any], audit_path: str | Path) -> Path:
    target = Path(audit_path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return target
