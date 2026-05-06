from pathlib import Path as FilePath
from uuid import uuid4

from fastapi import FastAPI, File, Form, HTTPException, Path, Query, UploadFile
from fastapi.responses import FileResponse
from pydantic import BaseModel

from src.services.file_task_service import FileTaskService
from src.services.glossary_service import validate_export_format
from src.services.llm_config_service import default_llm_config_service
from src.services.training_service import chunk_training_text
from src.services.translation_service import validate_source_declaration, validate_translation_input
from src.services.workflow_service import WorkflowService


app = FastAPI(title="Cn-Jp Translate API")
_FILE_TASKS: dict[str, dict[str, object]] = {}
_UPLOAD_DIR = FilePath(".runtime") / "uploads"
_OUTPUT_DIR = FilePath(".runtime") / "outputs"
_WORKFLOW_SERVICE = WorkflowService(reference_dir=FilePath("references"))


class TranslateRequest(BaseModel):
    text: str
    source_declaration: str


class TrainRequest(BaseModel):
    text: str
    chunk_size: int = 4000


class FeedbackConfirmRequest(BaseModel):
    task_id: str
    confirmed: bool


class LLMConfigRequest(BaseModel):
    provider: str
    model: str
    api_key: str


class TranslateWorkflowReviseRequest(BaseModel):
    workflow_id: str
    user_revision_text: str


class TranslateWorkflowConfirmRequest(BaseModel):
    workflow_id: str
    confirmed: bool


class TrainingWorkflowActionRequest(BaseModel):
    workflow_id: str


def _store_upload(task_id: str, upload: UploadFile) -> FilePath:
    suffix = FilePath(upload.filename or "").suffix.lower()
    if suffix not in {".txt", ".md", ".docx"}:
        raise HTTPException(status_code=400, detail="unsupported file type")

    _UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    upload_path = _UPLOAD_DIR / f"{task_id}{suffix}"
    payload = upload.file.read()
    upload_path.write_bytes(payload)
    return upload_path


def _translate_workflow_payload(workflow: dict[str, object]) -> dict[str, object]:
    payload = dict(workflow)
    payload["copy_allowed"] = bool(workflow.get("confirmed", False))
    return payload


@app.post("/config/llm")
def save_llm_config(payload: LLMConfigRequest) -> dict[str, object]:
    service = default_llm_config_service()
    try:
        status = service.save(
            provider=payload.provider,
            model=payload.model,
            api_key=payload.api_key,
        )
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error
    return {"status": "ok", **status}


@app.get("/config/llm")
def get_llm_config() -> dict[str, object]:
    service = default_llm_config_service()
    return {"status": "ok", **service.get_status()}


@app.delete("/config/llm")
def clear_llm_config() -> dict[str, object]:
    service = default_llm_config_service()
    status = service.clear()
    return {"status": "ok", **status}


@app.post("/tasks/file")
def create_file_task(
    usage: str = Form(...),
    source_declaration: str = Form(...),
    file: UploadFile = File(...),
) -> dict[str, object]:
    source_ok, source_message = validate_source_declaration(source_declaration)
    if not source_ok:
        raise HTTPException(status_code=400, detail=source_message)

    normalized_usage = usage.strip().lower()
    if normalized_usage not in {"translate", "glossary"}:
        raise HTTPException(status_code=400, detail="usage must be translate or glossary")

    task_id = str(uuid4())
    upload_path = _store_upload(task_id, file)
    service = FileTaskService(output_dir=_OUTPUT_DIR)

    try:
        if normalized_usage == "translate":
            result = service.run_translate(upload_path, source_declaration=source_declaration)
            payload = {
                "task_id": task_id,
                "usage": "translate",
                "status": "completed",
                "download_ready": True,
                "output_path": result["output_path"],
                "source_declaration": result["source_declaration"],
            }
        else:
            result = service.run_glossary_import(upload_path, source_declaration=source_declaration)
            payload = {
                "task_id": task_id,
                "usage": "glossary",
                "status": "completed",
                "download_ready": False,
                "source_declaration": result["source_declaration"],
                "imported_count": result["imported_count"],
            }
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error

    _FILE_TASKS[task_id] = payload
    return payload


@app.get("/tasks/file/{task_id}")
def get_file_task(task_id: str = Path(..., min_length=1)) -> dict[str, object]:
    task = _FILE_TASKS.get(task_id)
    if task is None:
        raise HTTPException(status_code=404, detail="task not found")
    return task


@app.get("/downloads/{task_id}")
def download_file_task_output(task_id: str = Path(..., min_length=1)) -> FileResponse:
    task = _FILE_TASKS.get(task_id)
    if task is None:
        raise HTTPException(status_code=404, detail="task not found")
    if task.get("usage") != "translate":
        raise HTTPException(status_code=400, detail="download only available for translate task")

    output_path = FilePath(str(task.get("output_path", "")))
    if not output_path.exists():
        raise HTTPException(status_code=404, detail="output file not found")
    return FileResponse(path=output_path, filename=output_path.name)


@app.post("/tasks/translate")
def create_translate_task(payload: TranslateRequest) -> dict[str, object]:
    source_ok, source_message = validate_source_declaration(payload.source_declaration)
    if not source_ok:
        raise HTTPException(status_code=400, detail=source_message)

    text_ok, text_message = validate_translation_input(payload.text)
    if not text_ok:
        raise HTTPException(status_code=400, detail=text_message)

    return {
        "task": "translate",
        "accepted": True,
        "text_length": len(payload.text),
        "source_declaration": payload.source_declaration,
    }


@app.post("/tasks/train")
def create_train_task(payload: TrainRequest) -> dict[str, object]:
    try:
        chunks = chunk_training_text(payload.text, chunk_size=payload.chunk_size)
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error

    return {
        "task": "train",
        "accepted": True,
        "chunk_count": len(chunks),
    }


@app.get("/glossary/export")
def export_glossary(fmt: str = Query(default="json")) -> dict[str, object]:
    try:
        normalized_format = validate_export_format(fmt)
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error

    return {
        "status": "ok",
        "format": normalized_format,
        "data": [],
    }


@app.post("/feedback/confirm")
def submit_feedback_confirmation(payload: FeedbackConfirmRequest) -> dict[str, object]:
    return {"status": "ok", "task_id": payload.task_id, "confirmed": payload.confirmed}


@app.get("/tasks/{task_id}/events")
def list_task_events(task_id: str = Path(..., min_length=1)) -> dict[str, object]:
    return {"task_id": task_id, "events": []}


@app.post("/workflow/translate/start")
def start_translate_workflow(
    source_declaration: str = Form(...),
    file: UploadFile = File(...),
) -> dict[str, object]:
    source_ok, source_message = validate_source_declaration(source_declaration)
    if not source_ok:
        raise HTTPException(status_code=400, detail=source_message)

    workflow_id = str(uuid4())
    upload_path = _store_upload(workflow_id, file)
    try:
        text = upload_path.read_text(encoding="utf-8")
    except UnicodeDecodeError as error:
        raise HTTPException(status_code=400, detail="uploaded file must be valid UTF-8 text") from error

    workflow = _WORKFLOW_SERVICE.start_translate(
        source_declaration=source_declaration,
        filename=file.filename or upload_path.name,
        text=text,
    )
    return _translate_workflow_payload(workflow)


@app.post("/workflow/translate/revise")
def revise_translate_workflow(payload: TranslateWorkflowReviseRequest) -> dict[str, object]:
    try:
        workflow = _WORKFLOW_SERVICE.revise_translate(
            workflow_id=payload.workflow_id,
            user_revision_text=payload.user_revision_text,
        )
    except ValueError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error
    return _translate_workflow_payload(workflow)


@app.post("/workflow/translate/confirm")
def confirm_translate_workflow(payload: TranslateWorkflowConfirmRequest) -> dict[str, object]:
    try:
        workflow = _WORKFLOW_SERVICE.confirm_translate(
            workflow_id=payload.workflow_id,
            confirmed=payload.confirmed,
        )
    except ValueError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error
    return _translate_workflow_payload(workflow)


@app.get("/workflow/translate/{workflow_id}")
def get_translate_workflow(workflow_id: str = Path(..., min_length=1)) -> dict[str, object]:
    try:
        workflow = _WORKFLOW_SERVICE.get_translate(workflow_id)
    except ValueError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error
    return _translate_workflow_payload(workflow)


@app.post("/workflow/training/start")
def start_training_workflow(
    source_declaration: str = Form(...),
    raw_file: UploadFile = File(...),
    reference_file: UploadFile | None = File(default=None),
) -> dict[str, object]:
    source_ok, source_message = validate_source_declaration(source_declaration)
    if not source_ok:
        raise HTTPException(status_code=400, detail=source_message)

    workflow_id = str(uuid4())
    raw_upload_path = _store_upload(f"{workflow_id}-raw", raw_file)
    try:
        raw_text = raw_upload_path.read_text(encoding="utf-8")
    except UnicodeDecodeError as error:
        raise HTTPException(status_code=400, detail="uploaded file must be valid UTF-8 text") from error

    reference_text: str | None = None
    if reference_file is not None:
        reference_upload_path = _store_upload(f"{workflow_id}-reference", reference_file)
        try:
            reference_text = reference_upload_path.read_text(encoding="utf-8")
        except UnicodeDecodeError as error:
            raise HTTPException(status_code=400, detail="uploaded file must be valid UTF-8 text") from error

    try:
        workflow = _WORKFLOW_SERVICE.start_training(
            source_declaration=source_declaration,
            raw_filename=raw_file.filename or raw_upload_path.name,
            raw_text=raw_text,
            reference_text=reference_text,
            workflow_id=workflow_id,
        )
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error

    return workflow


@app.post("/workflow/training/reconcile")
def reconcile_training_workflow(payload: TrainingWorkflowActionRequest) -> dict[str, object]:
    try:
        workflow = _WORKFLOW_SERVICE.reconcile_training(payload.workflow_id)
    except ValueError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error
    return workflow


@app.post("/workflow/training/commit")
def commit_training_workflow(payload: TrainingWorkflowActionRequest) -> dict[str, object]:
    try:
        workflow = _WORKFLOW_SERVICE.commit_training(payload.workflow_id)
    except ValueError as error:
        if str(error) == "training workflow must be reconciled before commit":
            raise HTTPException(status_code=409, detail=str(error)) from error
        raise HTTPException(status_code=404, detail=str(error)) from error
    return workflow


@app.get("/workflow/training/{workflow_id}")
def get_training_workflow(workflow_id: str = Path(..., min_length=1)) -> dict[str, object]:
    try:
        workflow = _WORKFLOW_SERVICE.get_training(workflow_id)
    except ValueError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error
    return workflow
