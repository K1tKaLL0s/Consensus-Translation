from dataclasses import dataclass


@dataclass
class WorkflowStateStore:
    api_base_url: str = "http://127.0.0.1:8000"
    workflow_id: str | None = None
    stage: str = "idle"
    copy_allowed: bool = False
    latest_text: str = ""

    def set_translate_state(
        self,
        workflow_id: str,
        stage: str,
        latest_text: str,
        confirmed: bool,
    ) -> None:
        self.workflow_id = workflow_id
        self.stage = stage
        self.latest_text = latest_text
        self.copy_allowed = bool(confirmed)
