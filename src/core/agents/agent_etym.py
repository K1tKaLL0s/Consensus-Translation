from src.core.llm_router import LLMRouter


def analyze_etymology(
    term: str,
    context: str,
    provider: str = "gemini",
) -> dict[str, str]:
    context_snippet = context[:200]
    prompt = (
        "Analyze etymology for the term in context.\n"
        f"term: {term}\n"
        f"context: {context_snippet}"
    )
    router = LLMRouter()
    analysis = router.generate(provider=provider, prompt=prompt)
    return {
        "term": term,
        "context": context_snippet,
        "provider": provider,
        "analysis": analysis,
    }
