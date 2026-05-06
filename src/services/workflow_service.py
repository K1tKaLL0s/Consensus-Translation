from pathlib import Path
from uuid import uuid4

from src.services.revision_service import classify_revision


class WorkflowService:
    def __init__(self, reference_dir: Path | str) -> None:
        self._reference_dir = Path(reference_dir)
        self._translate_workflows: dict[str, dict[str, object]] = {}
        self._training_workflows: dict[str, dict[str, object]] = {}

    def start_translate(self, source_declaration: str, filename: str, text: str) -> dict[str, object]:
        workflow_id = str(uuid4())
        workflow = {
            "workflow_id": workflow_id,
            "source_declaration": source_declaration,
            "filename": filename,
            "original_text": text,
            "current_text": text,
            "revision": None,
            "confirmed": False,
            "status": "translate_started",
            "glossary_write_count": 0,
        }
        self._translate_workflows[workflow_id] = workflow
        return workflow

    def revise_translate(self, workflow_id: str, user_revision_text: str) -> dict[str, object]:
        workflow = self._get_translate_workflow(workflow_id)
        revision = classify_revision(
            original_text=str(workflow["original_text"]),
            revised_text=user_revision_text,
        )
        workflow["current_text"] = user_revision_text
        workflow["revision"] = revision
        workflow["status"] = "translate_revised"
        return workflow

    def confirm_translate(self, workflow_id: str, confirmed: bool) -> dict[str, object]:
        workflow = self._get_translate_workflow(workflow_id)
        previously_confirmed = bool(workflow["confirmed"])

        workflow["confirmed"] = confirmed
        workflow["status"] = "translate_confirmed" if confirmed else "translate_rejected"

        if confirmed and not previously_confirmed:
            workflow["glossary_write_count"] = int(workflow["glossary_write_count"]) + 1

        return workflow

    def get_translate(self, workflow_id: str) -> dict[str, object]:
        return self._get_translate_workflow(workflow_id)

    def start_training(
        self,
        source_declaration: str,
        raw_filename: str,
        raw_text: str,
        reference_text: str | None,
        workflow_id: str | None = None,
    ) -> dict[str, object]:
        resolved_reference_text = reference_text
        reference_path: str | None = None

        if resolved_reference_text is None:
            file_path = self._reference_dir / f"{source_declaration}.txt"
            if not file_path.exists():
                raise ValueError("reference text is required")
            resolved_reference_text = file_path.read_text(encoding="utf-8")
            reference_path = str(file_path)

        resolved_workflow_id = workflow_id or str(uuid4())
        workflow = {
            "workflow_id": resolved_workflow_id,
            "source_declaration": source_declaration,
            "raw_filename": raw_filename,
            "raw_text": raw_text,
            "reference_text": resolved_reference_text,
            "reference_path": reference_path,
            "reconciliation": None,
            "reconciled": False,
            "committed": False,
            "commit_count": 0,
            "status": "training_started",
        }

        self._training_workflows[resolved_workflow_id] = workflow
        return workflow

    def reconcile_training(self, workflow_id: str) -> dict[str, object]:
        workflow = self._get_training_workflow(workflow_id)
        reconciliation = classify_revision(
            original_text=str(workflow["raw_text"]),
            revised_text=str(workflow["reference_text"]),
        )
        workflow["reconciliation"] = reconciliation
        workflow["reconciled"] = True
        workflow["status"] = "training_reconciled"
        return workflow

    def commit_training(self, workflow_id: str) -> dict[str, object]:
        workflow = self._get_training_workflow(workflow_id)
        if not bool(workflow["reconciled"]):
            raise ValueError("training workflow must be reconciled before commit")
        if not bool(workflow["committed"]):
            workflow["committed"] = True
            workflow["commit_count"] = int(workflow["commit_count"]) + 1
        workflow["status"] = "training_committed"
        return workflow

    def get_training(self, workflow_id: str) -> dict[str, object]:
        return self._get_training_workflow(workflow_id)

    def _get_translate_workflow(self, workflow_id: str) -> dict[str, object]:
        if workflow_id not in self._translate_workflows:
            raise ValueError("translate workflow not found")
        return self._translate_workflows[workflow_id]

    def _get_training_workflow(self, workflow_id: str) -> dict[str, object]:
        if workflow_id not in self._training_workflows:
            raise ValueError("training workflow not found")
        return self._training_workflows[workflow_id]
