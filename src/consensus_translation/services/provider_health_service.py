from __future__ import annotations

from consensus_translation.product_contracts import ProviderHealthDTO


def _is_mock_provider(provider: object) -> bool:
    return bool(getattr(provider, "is_mock", False)) or str(
        getattr(provider, "provider_kind", "")
    ).lower() == "mock"


def provider_health_dto(
    provider: object,
    *,
    latency: float | None = None,
    reliability_score: float | None = None,
    fallback_chain: tuple[str, ...] | None = None,
) -> ProviderHealthDTO:
    provider_id = str(getattr(provider, "provider_id", "unknown"))
    is_mock = _is_mock_provider(provider)
    active_latency = float(
        latency
        if latency is not None
        else getattr(provider, "latency", 0.0) or 0.0
    )
    raw_reliability = (
        reliability_score
        if reliability_score is not None
        else getattr(provider, "confidence", getattr(provider, "_confidence", 0.75))
    )
    reliability = max(0.0, min(float(raw_reliability or 0.0), 1.0))
    status = "mock" if is_mock else ("ready" if reliability >= 0.5 else "degraded")
    return ProviderHealthDTO(
        status=status,  # type: ignore[arg-type]
        latency=active_latency,
        reliability_score=reliability,
        fallback_chain=fallback_chain or (provider_id,),
        is_mock=is_mock,
        is_production_ready=not is_mock and status in {"ready", "degraded"},
    )

