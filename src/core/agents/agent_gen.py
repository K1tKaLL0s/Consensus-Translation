from src.core.llm_router import LLMRouter


def generate_candidates(term: str) -> dict[str, str]:
    clean = term.strip()
    if not clean:
        raise ValueError("term must not be blank")

    router = LLMRouter()
    context = clean[:200]
    return {
        "gen_a": router.generate(
            provider="deepseek",
            prompt=f"Generate candidate A for: {context}",
        ),
        "gen_b": router.generate(
            provider="gemini",
            prompt=f"Generate candidate B for: {context}",
        ),
        "gen_c": router.generate(
            provider="watsonx",
            prompt=f"Generate candidate C for: {context}",
        ),
    }
