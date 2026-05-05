from src.core.llm_router import LLMRouter


def analyze_etymology(
    term: str,
    context: str,
    provider: str = "gemini",
) -> dict[str, str]:
    prompt = (
        "Analyze etymology for the term in context.\n"
        f"term: {term}\n"
        f"context: {context}"
    )
    router = LLMRouter()
    analysis = router.generate(provider=provider, prompt=prompt)
    return {
        "term": term,
        "context": context,
        "provider": provider,
        "analysis": analysis,
    }
