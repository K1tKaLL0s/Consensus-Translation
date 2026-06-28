from __future__ import annotations

from dataclasses import asdict, is_dataclass
from enum import Enum
import json
from typing import Any

from PySide6.QtCore import QObject, Slot

from consensus_translation.product_contracts import (
    ErrorCode,
    consensus_to_dto,
    map_task_status,
)
from consensus_translation.services.capability_service import (
    get_capabilities,
    get_self_decision_status,
)
from consensus_translation.services.provider_health_service import provider_health_dto
from consensus_translation.desktop_qt.application_service import DesktopApplicationService


def _jsonable(value: object) -> object:
    if is_dataclass(value):
        return {key: _jsonable(item) for key, item in asdict(value).items()}
    if isinstance(value, Enum):
        return value.value
    if isinstance(value, dict):
        return {str(key): _jsonable(item) for key, item in value.items()}
    if isinstance(value, (list, tuple, set)):
        return [_jsonable(item) for item in value]
    return value


def _json_dumps(payload: object) -> str:
    return json.dumps(_jsonable(payload), ensure_ascii=False, sort_keys=True)


def _json_loads(payload_json: str) -> dict[str, Any]:
    try:
        payload = json.loads(payload_json or "{}")
    except json.JSONDecodeError as exc:
        raise ValueError(f"invalid JSON payload: {exc}") from exc
    if not isinstance(payload, dict):
        raise ValueError("payload must be a JSON object")
    return payload


class ReactContractBridge(QObject):
    """QWebChannel boundary for the React UI contract layer."""

    def __init__(self, service: DesktopApplicationService) -> None:
        super().__init__()
        self.service = service

    @Slot(result=str)
    def getCapabilities(self) -> str:
        capabilities = get_capabilities(
            allow_mock_provider=bool(self.service.controller.config.allow_mock_providers),
            self_decision_status=self._self_decision_status(),
        )
        return _json_dumps(capabilities)

    @Slot(result=str)
    def getSelfDecisionStatus(self) -> str:
        return _json_dumps(self._self_decision_status())

    @Slot(result=str)
    def getProviderHealth(self) -> str:
        health = [
            provider_health_dto(provider)
            for provider in getattr(self.service.controller, "providers", [])
        ]
        return _json_dumps(health)

    @Slot(str, result=str)
    def translateText(self, payload_json: str) -> str:
        try:
            payload = _json_loads(payload_json)
            workflow_mode = str(payload.get("workflow_mode", "") or "")
            execution_mode = str(payload.get("mode", "") or "")
            if workflow_mode == "standard" and execution_mode in {"", "standard"}:
                execution_mode = "local"
            result = self.service.translate_text(
                str(payload.get("text", "")),
                source_lang=str(payload.get("source_lang", "") or ""),
                target_lang=str(payload.get("target_lang", "") or ""),
                topic=str(payload.get("topic", "") or ""),
                mode=execution_mode,
            )
            run = (
                self.service._last_translation.initial_task.run
                if self.service._last_translation is not None
                else None
            )
            if run is not None:
                consensus = consensus_to_dto(run.decision)
                task_status = map_task_status(run.contract.status.value)
            else:
                consensus = {
                    "final_text": result.final_text,
                    "vote_map": {},
                    "conflicts": [],
                    "arbitration_reason": "",
                    "alignment_level": "heuristic",
                    "requires_review": False,
                }
                task_status = map_task_status("completed")
            return _json_dumps(
                {
                    "ok": True,
                    "run_id": result.run_id,
                    "task_status": task_status,
                    "error_code": ErrorCode.NONE,
                    "consensus": consensus,
                    "candidates": result.candidates,
                }
            )
        except Exception as exc:  # noqa: BLE001 - converts UI boundary errors to DTO.
            return _json_dumps(
                {
                    "ok": False,
                    "run_id": "",
                    "task_status": map_task_status("failed"),
                    "error_code": _error_code_for_exception(exc),
                    "message": str(exc),
                    "consensus": {
                        "final_text": "",
                        "vote_map": {},
                        "conflicts": [],
                        "arbitration_reason": "",
                        "alignment_level": "heuristic",
                        "requires_review": True,
                    },
                    "candidates": [],
                }
            )

    @Slot(str, result=str)
    def previewRemoteCalls(self, payload_json: str) -> str:
        payload = _json_loads(payload_json)
        lines = self.service.preview_remote_calls(
            str(payload.get("text", "")),
            source_lang=str(payload.get("source_lang", "") or ""),
            target_lang=str(payload.get("target_lang", "") or ""),
            topic=str(payload.get("topic", "") or ""),
            mode=str(payload.get("mode", "") or ""),
        )
        return _json_dumps({"ok": True, "lines": lines})

    @Slot(result=str)
    def listHistory(self) -> str:
        records = [
            {
                "id": record.run_id or str(index),
                "source_text": record.source_text,
                "translated_text": record.translated_text,
                "source_language": record.source_language,
                "target_language": record.target_language,
                "topic": record.topic,
                "mode": record.mode,
                "run_id": record.run_id,
                "workflow_status": record.workflow_status,
                "consensus_score": record.consensus_score,
                "confidence_level": record.confidence_level,
                "conflicts": list(record.conflicts),
                "arbitration_reason": record.arbitration_reason,
                "requires_human_review": record.requires_human_review,
                "rating": record.rating,
            }
            for index, record in enumerate(self.service.list_translation_history(), start=1)
        ]
        return _json_dumps(records)

    @Slot(result=str)
    def getTermbase(self) -> str:
        return _json_dumps(self.service.export_current_topic_lexicon())

    @Slot(str, result=str)
    def saveProviderSettings(self, payload_json: str) -> str:
        payload = _json_loads(payload_json)
        config = self.service.save_provider_settings(
            provider_id=str(payload.get("provider_id", "")),
            base_url=str(payload.get("base_url", "")),
            model=str(payload.get("model", "")),
            api_key=str(payload.get("api_key", "")),
            estimated_cost=float(payload.get("estimated_cost", 0.0) or 0.0),
            enabled=bool(payload.get("enabled", True)),
        )
        return _json_dumps({"ok": True, "provider_id": config.provider_id})

    @Slot(str, result=str)
    def smokeProviders(self, payload_json: str) -> str:
        payload = _json_loads(payload_json)
        lines = self.service.smoke_test_providers(
            sample_text=str(payload.get("sample_text", "hello") or "hello")
        )
        return _json_dumps({"ok": True, "lines": lines})

    def _self_decision_status(self) -> object:
        config = self.service.controller.config
        return get_self_decision_status(
            training_text=config.training_file,
            validation_text=config.validation_file,
            api_enabled=config.api_enabled,
            budget_limit=config.budget_limit,
            local_provider_count=sum(
                1
                for provider in getattr(self.service.controller, "providers", [])
                if not bool(getattr(provider, "requires_api", False))
            ),
            cloud_provider_count=sum(
                1
                for provider in getattr(self.service.controller, "providers", [])
                if bool(getattr(provider, "requires_api", False))
            ),
        )


def _error_code_for_exception(exc: Exception) -> ErrorCode:
    text = str(exc).lower()
    if "mock providers are disabled" in text:
        return ErrorCode.MOCK_PROVIDER_BLOCKED
    if "budget" in text:
        return ErrorCode.BUDGET_EXCEEDED
    if "confirmation" in text:
        return ErrorCode.HUMAN_CONFIRMATION_REQUIRED
    if "provider" in text:
        return ErrorCode.PROVIDER_UNAVAILABLE
    return ErrorCode.STORE_COMMIT_FAILED
