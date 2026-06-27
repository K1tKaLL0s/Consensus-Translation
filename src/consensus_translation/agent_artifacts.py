from __future__ import annotations

import json
import re
from pathlib import Path

from consensus_translation.agent_continuation import (
    ContextManagedTranslationResult,
    ManagedTranslationTask,
)


ARTIFACT_VERSION = "desktop-agent-artifacts-v1"


def _safe_base_name(base_name: str | None) -> str:
    raw = (base_name or "translation").strip() or "translation"
    safe = re.sub(r"[^A-Za-z0-9._-]+", "_", raw)
    return safe.strip("._") or "translation"


def _write_text(path: Path, text: str) -> Path:
    path.write_text(text, encoding="utf-8")
    return path


def _write_json(path: Path, payload: object) -> Path:
    path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True),
        encoding="utf-8",
    )
    return path


def _run_payload(task: ManagedTranslationTask) -> dict[str, object] | None:
    if task.run is None:
        return None
    return {
        "run_id": task.run.contract.run_id,
        "mode": task.run.contract.mode.value,
        "status": task.run.contract.status.value,
        "input_refs": list(task.run.contract.input_refs),
        "provider_policy": dict(task.run.contract.provider_policy),
        "budget": dict(task.run.contract.budget),
        "trace": list(task.run.contract.trace),
        "final_text": task.run.decision.final_text,
        "final_score": task.run.decision.final_score,
        "decision_reason": task.run.decision.decision_reason,
        "candidate_provider_ids": [
            candidate.provider_id for candidate in task.run.candidates
        ],
    }


def _task_payload(task: ManagedTranslationTask) -> dict[str, object]:
    payload: dict[str, object] = {
        "task_id": task.task_id,
        "task_type": task.task_type,
        "source_text": task.source_text,
        "inherited_brief": task.inherited_brief,
        "source_task_ids": list(task.source_task_ids or []),
        "verification": task.verification,
        "run": _run_payload(task),
    }
    if task.run is not None:
        payload["translated_text"] = task.run.decision.final_text
    return payload


def _segments_payload(result: ContextManagedTranslationResult) -> list[dict[str, object]]:
    return [
        _task_payload(result.initial_task),
        *[_task_payload(task) for task in result.continuation_tasks],
        _task_payload(result.stitch_task),
    ]


def _context_payload(result: ContextManagedTranslationResult) -> dict[str, object]:
    slices = result.context_plan.slices
    return {
        "estimated_input_tokens": result.context_plan.estimated_input_tokens,
        "available_input_tokens": result.context_plan.available_input_tokens,
        "slice_count": len(slices),
        "pending_slice_count": sum(1 for item in slices if not item.fits_current_task),
        "slices": [
            {
                "index": item.index,
                "estimated_tokens": item.estimated_tokens,
                "fits_current_task": item.fits_current_task,
                "text_preview": item.text[:120],
            }
            for item in slices
        ],
    }


def export_translation_artifacts(
    result: ContextManagedTranslationResult,
    output_dir: str | Path,
    base_name: str | None = None,
    project_id: str = "default",
    config: dict[str, object] | None = None,
) -> dict[str, Path]:
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    stem = _safe_base_name(base_name)

    artifacts = {
        "final_text": output_path / f"{stem}.translation.txt",
        "translation_brief": output_path / f"{stem}.brief.md",
        "verification": output_path / f"{stem}.verification.json",
        "segments": output_path / f"{stem}.segments.json",
        "manifest": output_path / f"{stem}.manifest.json",
    }

    _write_text(artifacts["final_text"], result.final_text)
    _write_text(artifacts["translation_brief"], result.translation_brief)
    _write_json(artifacts["verification"], result.verification)

    segments = _segments_payload(result)
    _write_json(artifacts["segments"], segments)

    manifest = {
        "artifact_version": ARTIFACT_VERSION,
        "project_id": project_id,
        "files": {key: path.name for key, path in artifacts.items() if key != "manifest"},
        "context": _context_payload(result),
        "verification": dict(result.verification),
        "tasks": [
            {
                "task_id": segment["task_id"],
                "task_type": segment["task_type"],
                "run_id": (
                    segment["run"]["run_id"]
                    if isinstance(segment.get("run"), dict)
                    else None
                ),
            }
            for segment in segments
        ],
        "config": dict(config or {}),
    }
    _write_json(artifacts["manifest"], manifest)
    return artifacts
