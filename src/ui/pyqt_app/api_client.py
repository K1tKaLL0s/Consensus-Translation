from pathlib import Path

import requests


class ApiClient:
    def __init__(self, base_url: str = "http://127.0.0.1:8000", timeout: float = 10.0) -> None:
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout

    def _url(self, path: str) -> str:
        return f"{self.base_url}{path}"

    def get_llm_config(self) -> dict[str, object]:
        response = requests.get(self._url("/config/llm"), timeout=self.timeout)
        response.raise_for_status()
        return response.json()

    def save_llm_config(self, provider: str, model: str, api_key: str) -> dict[str, object]:
        response = requests.post(
            self._url("/config/llm"),
            json={"provider": provider, "model": model, "api_key": api_key},
            timeout=self.timeout,
        )
        response.raise_for_status()
        return response.json()

    def delete_llm_config(self) -> dict[str, object]:
        response = requests.delete(self._url("/config/llm"), timeout=self.timeout)
        response.raise_for_status()
        return response.json()

    def start_translate_workflow(self, file_path: str, source_declaration: str) -> dict[str, object]:
        upload_name = Path(file_path).name
        with open(file_path, "rb") as handle:
            response = requests.post(
                self._url("/workflow/translate/start"),
                data={"source_declaration": source_declaration},
                files={"file": (upload_name, handle, "text/plain")},
                timeout=self.timeout,
            )
        response.raise_for_status()
        return response.json()

    def revise_translate_workflow(self, workflow_id: str, user_revision_text: str) -> dict[str, object]:
        response = requests.post(
            self._url("/workflow/translate/revise"),
            json={"workflow_id": workflow_id, "user_revision_text": user_revision_text},
            timeout=self.timeout,
        )
        response.raise_for_status()
        return response.json()

    def confirm_translate_workflow(self, workflow_id: str, confirmed: bool = True) -> dict[str, object]:
        response = requests.post(
            self._url("/workflow/translate/confirm"),
            json={"workflow_id": workflow_id, "confirmed": confirmed},
            timeout=self.timeout,
        )
        response.raise_for_status()
        return response.json()

    def get_translate_workflow(self, workflow_id: str) -> dict[str, object]:
        response = requests.get(self._url(f"/workflow/translate/{workflow_id}"), timeout=self.timeout)
        response.raise_for_status()
        return response.json()

    def start_training_workflow(
        self,
        raw_file_path: str,
        source_declaration: str,
        reference_file_path: str | None = None,
    ) -> dict[str, object]:
        files: dict[str, tuple[str, object, str]] = {}
        raw_handle = open(raw_file_path, "rb")
        files["raw_file"] = (Path(raw_file_path).name, raw_handle, "text/plain")
        reference_handle = None
        try:
            if reference_file_path:
                reference_handle = open(reference_file_path, "rb")
                files["reference_file"] = (Path(reference_file_path).name, reference_handle, "text/plain")
            response = requests.post(
                self._url("/workflow/training/start"),
                data={"source_declaration": source_declaration},
                files=files,
                timeout=self.timeout,
            )
        finally:
            raw_handle.close()
            if reference_handle is not None:
                reference_handle.close()
        response.raise_for_status()
        return response.json()

    def reconcile_training_workflow(self, workflow_id: str) -> dict[str, object]:
        response = requests.post(
            self._url("/workflow/training/reconcile"),
            json={"workflow_id": workflow_id},
            timeout=self.timeout,
        )
        response.raise_for_status()
        return response.json()

    def commit_training_workflow(self, workflow_id: str) -> dict[str, object]:
        response = requests.post(
            self._url("/workflow/training/commit"),
            json={"workflow_id": workflow_id},
            timeout=self.timeout,
        )
        response.raise_for_status()
        return response.json()

    def get_training_workflow(self, workflow_id: str) -> dict[str, object]:
        response = requests.get(self._url(f"/workflow/training/{workflow_id}"), timeout=self.timeout)
        response.raise_for_status()
        return response.json()
