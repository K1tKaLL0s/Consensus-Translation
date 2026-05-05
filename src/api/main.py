from typing import Literal

from fastapi import FastAPI, HTTPException, Path, Query
from pydantic import BaseModel

from src.services.glossary_service import validate_export_format
from src.services.training_service import chunk_training_text
from src.services.translation_service import validate_source_declaration, validate_translation_input


app = FastAPI(title="Cn-Jp Translate API")


class TranslateRequest(BaseModel):
    text: str
    source_declaration: str


class TrainRequest(BaseModel):
    text: str
    chunk_size: int = 4000


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
def export_glossary(fmt: Literal["csv", "xlsx", "json"] = Query(default="json")) -> dict[str, object]:
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
def submit_feedback_confirmation() -> dict[str, str]:
    return {"status": "placeholder"}


@app.get("/tasks/{task_id}/events")
def list_task_events(task_id: str = Path(..., min_length=1)) -> dict[str, object]:
    return {"task_id": task_id, "events": []}
