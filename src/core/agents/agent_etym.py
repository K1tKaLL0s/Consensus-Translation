from src.core.llm_router import LLMRouter


def analyze_etymology(
    term: str,
    context: str,
    provider: str = "gemini",
) -> dict[str, str]:
    clean_term = term.strip()
    if not clean_term:
        raise ValueError("term must not be blank")

    context_snippet = context.strip()[:200] if context else ""
    prompt = (
        "Analyze etymology for the term in context.\n"
        f"term: {clean_term}\n"
        f"context: {context_snippet}"
    )
    router = LLMRouter()
    analysis = router.generate(provider=provider, prompt=prompt)
    return {
        "term": clean_term,
        "context": context_snippet,
        "provider": provider,
        "analysis": analysis,
    }
