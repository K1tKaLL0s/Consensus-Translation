from __future__ import annotations

from dataclasses import dataclass, field
import json
from pathlib import Path
import re
import subprocess
from tempfile import TemporaryDirectory
import time
from typing import Callable, Protocol

import requests

from consensus_translation.evaluation import evaluate_translation


@dataclass(frozen=True)
class EvaluationRequest:
    source_text: str
    candidate_text: str
    reference_text: str
    source_lang: str
    target_lang: str
    topic: str | None
    round_index: int


@dataclass(frozen=True)
class EvaluationResult:
    evaluator_id: str
    score: float
    metrics: dict[str, float]
    rationale: str = ""
    warnings: list[str] = field(default_factory=list)
    cost: float = 0.0
    latency: float = 0.0
    requires_human_review: bool = False


class TranslationEvaluator(Protocol):
    evaluator_id: str
    requires_api: bool
    estimated_cost: float

    def evaluate(self, request: EvaluationRequest) -> EvaluationResult:
        ...


def _clamp_score(value: object) -> float:
    try:
        score = float(value)
    except (TypeError, ValueError):
        return 0.0
    return max(0.0, min(score, 1.0))


class DeterministicTranslationEvaluator:
    evaluator_id = "deterministic"
    requires_api = False
    estimated_cost = 0.0

    def evaluate(self, request: EvaluationRequest) -> EvaluationResult:
        metrics = evaluate_translation(
            request.candidate_text,
            request.reference_text,
        )
        return EvaluationResult(
            evaluator_id=self.evaluator_id,
            score=_clamp_score(metrics["overall"]),
            metrics={key: float(value) for key, value in metrics.items()},
        )


class OpenAICompatibleJudgeEvaluator:
    requires_api = True

    def __init__(
        self,
        evaluator_id: str,
        base_url: str,
        model: str,
        api_key: str,
        estimated_cost: float = 0.0,
        timeout: float = 60.0,
        post_fn: Callable[..., object] | None = None,
    ) -> None:
        self.evaluator_id = evaluator_id
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.api_key = api_key
        self.estimated_cost = estimated_cost
        self.timeout = timeout
        self._post = post_fn or requests.post

    def _build_prompt(self, request: EvaluationRequest) -> str:
        return (
            "You are evaluating machine translation quality for a controlled "
            "workflow agent. Return strict JSON only with keys: score "
            "(number from 0 to 1) and rationale (short string).\n"
            f"Language pair: {request.source_lang}->{request.target_lang}\n"
            f"Topic: {request.topic or 'uncategorized'}\n"
            f"Round: {request.round_index}\n\n"
            f"Source:\n{request.source_text}\n\n"
            f"Candidate translation:\n{request.candidate_text}\n\n"
            f"Reference or validation target:\n{request.reference_text}"
        )

    @staticmethod
    def _parse_json_payload(content: str) -> tuple[float, str, list[str]]:
        warnings: list[str] = []
        raw = content.strip()
        try:
            parsed = json.loads(raw)
        except json.JSONDecodeError:
            match = re.search(r"\{.*\}", raw, flags=re.DOTALL)
            if match is None:
                return 0.0, "", ["llm-judge-invalid-json"]
            try:
                parsed = json.loads(match.group(0))
            except json.JSONDecodeError:
                return 0.0, "", ["llm-judge-invalid-json"]

        if not isinstance(parsed, dict):
            return 0.0, "", ["llm-judge-invalid-json"]
        score = _clamp_score(parsed.get("score"))
        rationale = str(parsed.get("rationale", ""))
        if "score" not in parsed:
            warnings.append("llm-judge-missing-score")
        return score, rationale, warnings

    def evaluate(self, request: EvaluationRequest) -> EvaluationResult:
        response = self._post(
            f"{self.base_url}/chat/completions",
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            },
            json={
                "model": self.model,
                "messages": [
                    {
                        "role": "user",
                        "content": self._build_prompt(request),
                    }
                ],
                "temperature": 0.0,
            },
            timeout=self.timeout,
        )
        response.raise_for_status()
        payload = response.json()
        content = str(payload["choices"][0]["message"]["content"])
        score, rationale, warnings = self._parse_json_payload(content)
        usage = payload.get("usage") if isinstance(payload, dict) else None
        total_tokens = 0.0
        if isinstance(usage, dict):
            total_tokens = float(usage.get("total_tokens", 0) or 0)
        return EvaluationResult(
            evaluator_id=self.evaluator_id,
            score=score,
            metrics={"llm_score": score, "total_tokens": total_tokens},
            rationale=rationale,
            warnings=warnings,
            cost=self.estimated_cost,
            requires_human_review=bool(warnings),
        )


class CometTranslationEvaluator:
    requires_api = False
    estimated_cost = 0.0

    def __init__(
        self,
        model: object | None = None,
        model_name: str = "Unbabel/wmt22-comet-da",
        evaluator_id: str = "comet",
        batch_size: int = 8,
        gpus: int = 0,
        loader_fn: Callable[[str], object] | None = None,
    ) -> None:
        self.evaluator_id = evaluator_id
        self.model_name = model_name
        self.batch_size = batch_size
        self.gpus = gpus
        self._model = model
        self._loader_fn = loader_fn

    def _load_model(self) -> object:
        if self._model is not None:
            return self._model
        if self._loader_fn is not None:
            self._model = self._loader_fn(self.model_name)
            return self._model

        try:
            from comet import download_model, load_from_checkpoint
        except ImportError as exc:
            raise RuntimeError(
                "COMET evaluator requires the optional unbabel-comet runtime"
            ) from exc

        model_path = download_model(self.model_name)
        self._model = load_from_checkpoint(model_path)
        return self._model

    @staticmethod
    def _extract_prediction_score(prediction: object) -> float:
        if isinstance(prediction, dict):
            scores = prediction.get("scores")
            if isinstance(scores, list) and scores:
                return _clamp_score(scores[0])
            if "system_score" in prediction:
                return _clamp_score(prediction["system_score"])

        scores = getattr(prediction, "scores", None)
        if isinstance(scores, list) and scores:
            return _clamp_score(scores[0])
        system_score = getattr(prediction, "system_score", None)
        if system_score is not None:
            return _clamp_score(system_score)
        return 0.0

    def evaluate(self, request: EvaluationRequest) -> EvaluationResult:
        model = self._load_model()
        prediction = model.predict(
            [
                {
                    "src": request.source_text,
                    "mt": request.candidate_text,
                    "ref": request.reference_text,
                }
            ],
            batch_size=self.batch_size,
            gpus=self.gpus,
        )
        score = self._extract_prediction_score(prediction)
        return EvaluationResult(
            evaluator_id=self.evaluator_id,
            score=score,
            metrics={"comet_score": score},
        )


class ExternalCometTranslationEvaluator:
    requires_api = False
    estimated_cost = 0.0

    def __init__(
        self,
        command: str = "comet-score",
        model_name: str = "Unbabel/wmt22-comet-da",
        model_storage_path: str | Path | None = None,
        evaluator_id: str = "comet-external",
        batch_size: int = 8,
        gpus: int = 0,
        timeout: float = 900.0,
        runner: Callable[[list[str], float], object] | None = None,
    ) -> None:
        self.command = command
        self.model_name = model_name
        self.model_storage_path = (
            Path(model_storage_path) if model_storage_path else None
        )
        self.evaluator_id = evaluator_id
        self.batch_size = batch_size
        self.gpus = gpus
        self.timeout = timeout
        self._runner = runner or self._run_command

    @staticmethod
    def _run_command(command: list[str], timeout: float) -> object:
        return subprocess.run(
            command,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=timeout,
            check=False,
        )

    @staticmethod
    def _single_line(text: str) -> str:
        return " ".join(text.splitlines()).strip()

    @staticmethod
    def _read_score(path: Path) -> float:
        payload = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(payload, dict):
            raise RuntimeError("COMET output JSON must be an object")
        for records in payload.values():
            if not isinstance(records, list) or not records:
                continue
            first = records[0]
            if isinstance(first, dict) and "COMET" in first:
                return _clamp_score(first["COMET"])
        raise RuntimeError("COMET output JSON does not contain a COMET score")

    def evaluate(self, request: EvaluationRequest) -> EvaluationResult:
        started = time.perf_counter()
        with TemporaryDirectory(prefix="consensus-comet-") as temp_dir_text:
            temp_dir = Path(temp_dir_text)
            source_path = temp_dir / "source.txt"
            candidate_path = temp_dir / "candidate.txt"
            reference_path = temp_dir / "reference.txt"
            output_path = temp_dir / "result.json"
            source_path.write_text(
                self._single_line(request.source_text) + "\n",
                encoding="utf-8",
            )
            candidate_path.write_text(
                self._single_line(request.candidate_text) + "\n",
                encoding="utf-8",
            )
            reference_path.write_text(
                self._single_line(request.reference_text) + "\n",
                encoding="utf-8",
            )
            command = [
                self.command,
                "-s",
                str(source_path),
                "-t",
                str(candidate_path),
                "-r",
                str(reference_path),
                "--model",
                self.model_name,
                "--batch_size",
                str(self.batch_size),
                "--gpus",
                str(self.gpus),
                "--quiet",
                "--to_json",
                str(output_path),
            ]
            if self.model_storage_path is not None:
                self.model_storage_path.mkdir(parents=True, exist_ok=True)
                command.extend(
                    ["--model_storage_path", str(self.model_storage_path)]
                )
            try:
                completed = self._runner(command, self.timeout)
            except FileNotFoundError as exc:
                raise RuntimeError(
                    f"COMET command not found: {self.command}"
                ) from exc
            except subprocess.TimeoutExpired as exc:
                raise RuntimeError("COMET evaluation timed out") from exc
            returncode = int(getattr(completed, "returncode", 1))
            if returncode != 0:
                stderr = str(getattr(completed, "stderr", "")).strip()
                stdout = str(getattr(completed, "stdout", "")).strip()
                raise RuntimeError(stderr or stdout or "COMET evaluation failed")
            if not output_path.exists():
                raise RuntimeError("COMET evaluation did not produce JSON output")
            score = self._read_score(output_path)
        return EvaluationResult(
            evaluator_id=self.evaluator_id,
            score=score,
            metrics={"comet_score": score},
            latency=time.perf_counter() - started,
        )
