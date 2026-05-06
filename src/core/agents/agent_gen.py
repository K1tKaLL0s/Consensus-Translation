import time

from src.core.llm_router import LLMRouter


def generate_candidates(
    term: str,
    providers: list[str] | None = None,
) -> dict[str, dict[str, str | float | None]]:
    clean = term.strip()
    if not clean:
        raise ValueError("term must not be blank")

    target_providers = providers or ["deepseek", "gemini", "watsonx"]
    router = LLMRouter()
    context = clean[:200]
    payload: dict[str, dict[str, str | float | None]] = {}
    for provider in target_providers:
        start = time.perf_counter()
        text = ""
        error = None
        try:
            text = router.generate(
                provider=provider,
                prompt=f"Generate candidate for: {context}",
            )
        except Exception as exc:
            error = str(exc)
        latency_ms = (time.perf_counter() - start) * 1000
        payload[provider] = {
            "provider": provider,
            "text": text,
            "latency_ms": float(latency_ms),
            "error": error,
        }

    return payload
