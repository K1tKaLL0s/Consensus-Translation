from enum import Enum
from typing import Literal
from uuid import uuid4

from pydantic import BaseModel, Field


class StageStatus(str, Enum):
    INGEST = "ingest"
    SEGMENT = "segment"
    ENGINE = "engine"
    CROSS_CHECK = "cross_check"
    MDWC = "mdwc"
    REVIEW = "review"
    FINALIZE = "finalize"


class StageEnvelope(BaseModel):
    current: StageStatus = StageStatus.INGEST
    progress: float = 0.0
    retry_count: int = 0
    error_code: str | None = None
    error_message: str | None = None


class TranslationJobContract(BaseModel):
    contract_version: Literal["1.0.0"] = "1.0.0"
    job_id: str
    mode: str
    source_lang: str
    target_lang: str
    topic: str
    stage_status: StageEnvelope = Field(default_factory=StageEnvelope)

    @classmethod
    def new_job(
        cls,
        mode: str,
        source_lang: str,
        target_lang: str,
        topic: str,
    ) -> "TranslationJobContract":
        job_id = f"job-{uuid4().hex[:16]}"
        return cls(
            job_id=job_id,
            mode=mode,
            source_lang=source_lang,
            target_lang=target_lang,
            topic=topic,
        )
