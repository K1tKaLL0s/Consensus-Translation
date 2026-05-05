from src.core.agents.agent_arb import compute_final_score, select_consensus
from src.core.agents.agent_etym import analyze_etymology
from src.core.agents.agent_gen import generate_candidates
from src.core.agents.agent_tex import extract_candidate_terms


class MAATCSOrchestrator:
    def run(self, raw_text: str, source_declaration: str) -> dict:
        terms = extract_candidate_terms(raw_text)

        etym_reports: list[dict[str, str]] = []
        candidate_pool: list[dict] = []

        for term in terms:
            etym_report = analyze_etymology(term=term, context=raw_text, provider="gemini")
            etym_reports.append(etym_report)

            generated = generate_candidates(term)
            for key, value in generated.items():
                final = compute_final_score(
                    mqm_score=0.9,
                    context_score=0.9,
                    frequency_score=0.9,
                )
                candidate_pool.append(
                    {
                        "term": term,
                        "source": key,
                        "text": value,
                        "final": final,
                    }
                )

        consensus = select_consensus(
            candidates=candidate_pool,
            threshold=0.9,
            kanji_raw=raw_text,
            romaji="",
        )

        return {
            "raw_text": raw_text,
            "source_declaration": source_declaration,
            "terms": terms,
            "etym_reports": etym_reports,
            "candidate_pool": candidate_pool,
            "consensus": consensus,
        }
