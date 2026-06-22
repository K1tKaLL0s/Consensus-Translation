from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from pathlib import Path

from consensus_translation.agent_artifacts import export_translation_artifacts
from consensus_translation.agent_context import ContextBudget
from consensus_translation.agent_contracts import AgentMode
from consensus_translation.agent_continuation import run_context_managed_translation
from consensus_translation.agent_providers import EchoModelProvider


DEFAULT_ACCEPTANCE_TEXT = "alpha beta\n\ngamma delta\n\nomega zeta"


@dataclass(frozen=True)
class LocalAcceptanceResult:
    ok: bool
    artifact_dir: Path
    final_text: str
    verification: dict[str, object]
    context: dict[str, object]
    task_types: list[str]
    artifacts: dict[str, Path]


def _context_summary(result) -> dict[str, object]:
    return {
        "estimated_input_tokens": result.context_plan.estimated_input_tokens,
        "available_input_tokens": result.context_plan.available_input_tokens,
        "slice_count": len(result.context_plan.slices),
        "pending_slice_count": sum(
            1 for item in result.context_plan.slices if not item.fits_current_task
        ),
    }


def _task_types(result) -> list[str]:
    return [
        result.initial_task.task_type,
        *[task.task_type for task in result.continuation_tasks],
        result.stitch_task.task_type,
    ]


def run_local_acceptance(
    output_dir: str | Path,
    project_id: str = "desktop-acceptance",
    sample_text: str = DEFAULT_ACCEPTANCE_TEXT,
) -> LocalAcceptanceResult:
    artifact_dir = Path(output_dir)
    result = run_context_managed_translation(
        text=sample_text,
        source_lang="en",
        target_lang="zh",
        topic="acceptance",
        mode=AgentMode.LEARNING,
        providers=[EchoModelProvider("acceptance-local", prefix="ZH:")],
        context_budget=ContextBudget(max_context_tokens=7, reserved_output_tokens=2),
        api_enabled=False,
        budget_limit=0.0,
    )
    artifacts = export_translation_artifacts(
        result=result,
        output_dir=artifact_dir,
        base_name=project_id,
        project_id=project_id,
        config={
            "source_lang": "en",
            "target_lang": "zh",
            "topic": "acceptance",
            "mode": AgentMode.LEARNING.value,
            "api_enabled": False,
            "acceptance": True,
        },
    )
    task_types = _task_types(result)
    context = _context_summary(result)
    ok = (
        result.verification.get("status") == "passed"
        and "initial_translation" in task_types
        and "continuation_translation" in task_types
        and "stitch_and_verify" in task_types
        and all(path.exists() for path in artifacts.values())
    )
    return LocalAcceptanceResult(
        ok=ok,
        artifact_dir=artifact_dir,
        final_text=result.final_text,
        verification=dict(result.verification),
        context=context,
        task_types=task_types,
        artifacts=artifacts,
    )


def format_acceptance_lines(result: LocalAcceptanceResult) -> list[str]:
    status = "ok" if result.ok else "failed"
    lines = [
        f"local acceptance: {status}",
        f"verification: {result.verification.get('status')}",
        (
            "context: "
            f"slices={result.context.get('slice_count')} | "
            f"pending={result.context.get('pending_slice_count')}"
        ),
        "tasks: " + ", ".join(result.task_types),
        f"artifact dir: {result.artifact_dir}",
    ]
    manifest = result.artifacts.get("manifest")
    if manifest is not None:
        lines.append(f"artifact manifest: {manifest}")
    return lines


def acceptance_report_payload(result: LocalAcceptanceResult) -> dict[str, object]:
    return {
        "ok": result.ok,
        "artifact_dir": str(result.artifact_dir),
        "final_text": result.final_text,
        "verification": dict(result.verification),
        "context": dict(result.context),
        "task_types": list(result.task_types),
        "artifacts": {
            name: str(path)
            for name, path in result.artifacts.items()
        },
    }


def write_acceptance_report(
    result: LocalAcceptanceResult,
    report_path: str | Path,
) -> Path:
    path = Path(report_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(
            acceptance_report_payload(result),
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
        ),
        encoding="utf-8",
    )
    return path


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--project-id", default="desktop-acceptance")
    parser.add_argument("--sample-text", default=DEFAULT_ACCEPTANCE_TEXT)
    parser.add_argument("--report-json")
    args = parser.parse_args(argv)

    result = run_local_acceptance(
        args.output_dir,
        project_id=args.project_id,
        sample_text=args.sample_text,
    )
    for line in format_acceptance_lines(result):
        print(line)
    if args.report_json:
        write_acceptance_report(result, args.report_json)
    return 0 if result.ok else 2


if __name__ == "__main__":
    raise SystemExit(main())
