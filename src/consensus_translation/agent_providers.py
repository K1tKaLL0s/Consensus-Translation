from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable, Protocol, cast

import requests  # type: ignore[import-untyped]

from consensus_translation.agent_contracts import TranslationCandidate


@dataclass(frozen=True)
class ProviderRequest:
    text: str
    source_lang: str
    target_lang: str
    topic: str | None
    round_index: int
    training_text: str | None = None
    continuation_brief: str | None = None
    conflict_points: list[str] = field(default_factory=list)
    lexicon_terms: dict[str, str] = field(default_factory=dict)
    lexicon_phrases: dict[str, str] = field(default_factory=dict)
    style_rules: dict[str, str] = field(default_factory=dict)


class ModelProvider(Protocol):
    provider_id: str
    requires_api: bool
    estimated_cost: float

    def translate(self, request: ProviderRequest) -> TranslationCandidate:
        ...


class StaticModelProvider:
    def __init__(
        self,
        provider_id: str,
        text: str,
        confidence: float,
        estimated_cost: float = 0.0,
        requires_api: bool = False,
        provider_kind: str = "test",
        provider_role: str = "static",
        is_mock: bool = False,
    ) -> None:
        self.provider_id = provider_id
        self._text = text
        self._confidence = confidence
        self.estimated_cost = estimated_cost
        self.requires_api = requires_api
        self.provider_kind = provider_kind
        self.provider_role = provider_role
        self.is_mock = is_mock
        self.calls = 0

    def translate(self, request: ProviderRequest) -> TranslationCandidate:
        self.calls += 1
        return TranslationCandidate(
            provider_id=self.provider_id,
            text=self._text,
            confidence=self._confidence,
            cost=self.estimated_cost,
            warnings=["mock-provider"] if self.is_mock else [],
            provider_kind=self.provider_kind,
            provider_role=self.provider_role,
            is_mock=self.is_mock,
            reasoning="static test provider candidate",
        )


class EchoModelProvider:
    def __init__(
        self,
        provider_id: str,
        prefix: str = "",
        confidence: float = 0.7,
    ) -> None:
        self.provider_id = provider_id
        self.prefix = prefix
        self.confidence = confidence
        self.estimated_cost = 0.0
        self.requires_api = False
        self.calls = 0

    def translate(self, request: ProviderRequest) -> TranslationCandidate:
        self.calls += 1
        return TranslationCandidate(
            provider_id=self.provider_id,
            text=f"{self.prefix}{request.text}",
            confidence=self.confidence,
            cost=0.0,
            warnings=["mock-provider", "echo-provider"],
            provider_kind="mock",
            provider_role="echo",
            is_mock=True,
            reasoning="Echo provider is a workflow placeholder and not a real translator.",
        )


class MockLocalModelProvider:
    requires_api = False
    estimated_cost = 0.0
    provider_kind = "local"
    is_mock = True

    def __init__(
        self,
        provider_id: str,
        provider_role: str,
        prefix: str,
        confidence: float = 0.6,
    ) -> None:
        self.provider_id = provider_id
        self.provider_role = provider_role
        self.prefix = prefix
        self.confidence = confidence
        self.calls = 0

    def translate(self, request: ProviderRequest) -> TranslationCandidate:
        self.calls += 1
        return TranslationCandidate(
            provider_id=self.provider_id,
            text=f"{self.prefix}{request.text}",
            confidence=self.confidence,
            provider_kind="local",
            provider_role=self.provider_role,
            is_mock=True,
            warnings=["mock-provider"],
            reasoning=(
                f"Mock local provider {self.provider_id} generated a deterministic "
                "candidate for workflow simulation."
            ),
        )


class MockCloudProvider:
    requires_api = False
    provider_kind = "cloud"
    provider_role = "cloud"
    is_mock = True

    def __init__(
        self,
        provider_id: str = "mockCloudProvider",
        confidence: float = 0.62,
        estimated_cost: float = 0.0,
    ) -> None:
        self.provider_id = provider_id
        self.confidence = confidence
        self.estimated_cost = estimated_cost
        self.calls = 0

    def translate(self, request: ProviderRequest) -> TranslationCandidate:
        self.calls += 1
        conflicts = ",".join(request.conflict_points) or "none"
        return TranslationCandidate(
            provider_id=self.provider_id,
            text=f"AI:{request.text}",
            confidence=self.confidence,
            cost=self.estimated_cost,
            provider_kind="cloud",
            provider_role="cloud",
            is_mock=True,
            warnings=["mock-provider"],
            reasoning=(
                "Mock cloud provider for controlled workflow simulation; "
                f"round={request.round_index}; conflicts={conflicts}"
            ),
        )


class LocalEngineModelProvider:
    requires_api = False
    estimated_cost = 0.0

    def __init__(
        self,
        provider_id: str,
        provider_role: str,
        engine_factory: Callable[[], object],
    ) -> None:
        self.provider_id = provider_id
        self.provider_role = provider_role
        self._engine_factory = engine_factory
        self._engine: object | None = None
        self.calls = 0

    def _engine_instance(self) -> object:
        if self._engine is None:
            self._engine = self._engine_factory()
        return self._engine

    def translate(self, request: ProviderRequest) -> TranslationCandidate:
        self.calls += 1
        engine = self._engine_instance()
        translate = getattr(engine, "translate")
        text, confidence = translate(
            request.text,
            request.source_lang,
            request.target_lang,
        )
        return TranslationCandidate(
            provider_id=self.provider_id,
            text=str(text),
            confidence=float(confidence),
            provider_kind="local",
            provider_role=self.provider_role,
            is_mock=False,
            reasoning=f"Real local engine provider {self.provider_id} completed translation.",
        )


class LocalWorkflowProvider:
    provider_id = "local-workflow"
    requires_api = False
    estimated_cost = 0.0

    def __init__(
        self,
        run_local_job_fn: Callable[..., dict[str, object]]
        | None = None,
    ) -> None:
        if run_local_job_fn is None:
            from consensus_translation.workflows import run_local_job

            self._run_local_job = run_local_job
        else:
            self._run_local_job = run_local_job_fn

    def translate(self, request: ProviderRequest) -> TranslationCandidate:
        result = self._run_local_job(
            request.text,
            request.source_lang,
            request.target_lang,
            request.topic,
        )
        warnings = []
        if result.get("needs_review") is True:
            warnings.append("local-workflow-needs-review")
        domain_hits_value = result.get("domain_hits")
        term_hits: dict[str, int] = {}
        if isinstance(domain_hits_value, dict):
            for key, value in domain_hits_value.items():
                try:
                    term_hits[str(key)] = int(str(value))
                except ValueError:
                    continue
        return TranslationCandidate(
            provider_id=self.provider_id,
            text=str(result.get("final_text", "")),
            confidence=float(str(result.get("final_score", 0.0) or 0.0)),
            cost=0.0,
            term_hits=term_hits,
            warnings=warnings,
            provider_kind="local",
            provider_role="local_workflow",
            is_mock=False,
            reasoning="Legacy local workflow provider wrapped existing two-engine workflow.",
        )


class OpenAICompatibleProvider:
    requires_api = True

    def __init__(
        self,
        provider_id: str,
        base_url: str,
        model: str,
        api_key: str,
        estimated_cost: float = 0.0,
        timeout: float = 60.0,
        post_fn: Callable[..., object] | None = None,
    ) -> None:
        self.provider_id = provider_id
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.api_key = api_key
        self.estimated_cost = estimated_cost
        self.timeout = timeout
        self._post = post_fn or requests.post

    def _build_prompt(self, request: ProviderRequest) -> str:
        conflict_text = ", ".join(request.conflict_points) or "none"
        training_text = ""
        if request.training_text:
            training_text = (
                "Approved training examples and style context:\n"
                f"{request.training_text[:4000]}\n\n"
            )
        continuation_text = ""
        if request.continuation_brief:
            continuation_text = (
                "Continuation brief from previous translation task:\n"
                f"{request.continuation_brief}\n\n"
            )
        lexicon_text = ""
        if request.lexicon_terms or request.lexicon_phrases or request.style_rules:
            lexicon_text = (
                "Confirmed glossary and style constraints:\n"
                f"terms={request.lexicon_terms}\n"
                f"phrases={request.lexicon_phrases}\n"
                f"style={request.style_rules}\n\n"
            )
        return (
            "You are a controlled workflow translation agent, not a chatbot.\n"
            f"Translate {request.source_lang}->{request.target_lang}.\n"
            f"Topic: {request.topic or 'uncategorized'}.\n"
            f"Round: {request.round_index}.\n"
            f"Conflict points to consider: {conflict_text}.\n"
            "Return only the translated text.\n\n"
            f"{training_text}"
            f"{continuation_text}"
            f"{lexicon_text}"
            f"Source:\n{request.text}"
        )

    def translate(self, request: ProviderRequest) -> TranslationCandidate:
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
                "temperature": 0.2,
            },
            timeout=self.timeout,
        )
        response = cast(Any, response)
        response.raise_for_status()
        payload = response.json()
        content = payload["choices"][0]["message"]["content"]
        usage = payload.get("usage") if isinstance(payload, dict) else None
        total_tokens = 0
        if isinstance(usage, dict):
            total_tokens = int(usage.get("total_tokens", 0) or 0)
        return TranslationCandidate(
            provider_id=self.provider_id,
            text=str(content).strip(),
            confidence=0.5,
            cost=self.estimated_cost,
            term_hits={"total_tokens": total_tokens},
            warnings=[],
            provider_kind="cloud",
            provider_role="cloud",
            is_mock=False,
            reasoning="OpenAI-compatible remote provider returned a candidate.",
        )
