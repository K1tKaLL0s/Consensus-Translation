from __future__ import annotations

from dataclasses import dataclass
from time import perf_counter

from consensus_translation.agent_providers import ModelProvider, ProviderRequest


@dataclass(frozen=True)
class ProviderSmokeResult:
    provider_id: str
    ok: bool
    sample_text: str
    translated_text: str
    latency_ms: int
    cost: float
    total_tokens: int
    warnings: list[str]
    error: str | None


def smoke_test_provider(
    provider: ModelProvider,
    source_lang: str = "en",
    target_lang: str = "zh",
    topic: str = "provider-smoke",
    sample_text: str = "hello",
    api_enabled: bool = True,
    allow_live_remote: bool = False,
) -> ProviderSmokeResult:
    started_at = perf_counter()
    if provider.requires_api and not api_enabled:
        return ProviderSmokeResult(
            provider_id=provider.provider_id,
            ok=False,
            sample_text=sample_text,
            translated_text="",
            latency_ms=int((perf_counter() - started_at) * 1000),
            cost=0.0,
            total_tokens=0,
            warnings=[],
            error="api disabled",
        )
    if provider.requires_api and not allow_live_remote:
        return ProviderSmokeResult(
            provider_id=provider.provider_id,
            ok=False,
            sample_text=sample_text,
            translated_text="",
            latency_ms=int((perf_counter() - started_at) * 1000),
            cost=0.0,
            total_tokens=0,
            warnings=[],
            error="live remote smoke requires explicit confirmation",
        )
    try:
        candidate = provider.translate(
            ProviderRequest(
                text=sample_text,
                source_lang=source_lang,
                target_lang=target_lang,
                topic=topic,
                round_index=1,
            )
        )
    except Exception as exc:
        return ProviderSmokeResult(
            provider_id=provider.provider_id,
            ok=False,
            sample_text=sample_text,
            translated_text="",
            latency_ms=int((perf_counter() - started_at) * 1000),
            cost=0.0,
            total_tokens=0,
            warnings=[],
            error=str(exc),
        )

    total_tokens = 0
    raw_total_tokens = candidate.term_hits.get("total_tokens")
    if raw_total_tokens is not None:
        total_tokens = int(raw_total_tokens)
    return ProviderSmokeResult(
        provider_id=provider.provider_id,
        ok=True,
        sample_text=sample_text,
        translated_text=candidate.text,
        latency_ms=int((perf_counter() - started_at) * 1000),
        cost=candidate.cost,
        total_tokens=total_tokens,
        warnings=list(candidate.warnings),
        error=None,
    )


def format_provider_smoke_lines(results: list[ProviderSmokeResult]) -> list[str]:
    ok_count = sum(1 for result in results if result.ok)
    failed_count = len(results) - ok_count
    lines = [
        (
            f"provider smoke: {len(results)} checked | "
            f"ok={ok_count} | failed={failed_count}"
        )
    ]
    for result in results:
        if result.ok:
            preview = " ".join(result.translated_text.split())
            lines.append(
                (
                    f"OK {result.provider_id} | latency={result.latency_ms}ms | "
                    f"tokens={result.total_tokens} | cost={result.cost} | {preview}"
                )
            )
        else:
            lines.append(
                (
                    f"FAIL {result.provider_id} | latency={result.latency_ms}ms | "
                    f"{result.error or 'unknown error'}"
                )
            )
    return lines
