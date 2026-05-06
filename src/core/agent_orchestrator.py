from typing import Any, TypedDict

from langgraph.graph import END, START, StateGraph

from src.core.agents.agent_arb import compute_final_score, select_consensus
from src.core.agents.agent_etym import analyze_etymology
from src.core.agents.agent_gen import generate_candidates
from src.core.agents.agent_tex import extract_candidate_terms


class OrchestratorState(TypedDict, total=False):
    raw_text: str
    source_declaration: str
    terms: list[str]
    etym_reports: list[dict[str, str]]
    candidate_pool: list[dict[str, Any]]
    consensus: dict[str, Any]
    unknown_only: bool


class MAATCSOrchestrator:
    def __init__(self) -> None:
        self._app = self._build_graph()

    def _build_graph(self):
        workflow = StateGraph(OrchestratorState)
        workflow.add_node("extract_terms", self._extract_terms)
        workflow.add_node("analyze_etymology", self._analyze_etymology)
        workflow.add_node("generate_candidates", self._generate_candidates)
        workflow.add_node("arbitrate", self._arbitrate)
        workflow.add_node("persist_and_render", self._persist_and_render)

        workflow.add_edge(START, "extract_terms")
        workflow.add_edge("extract_terms", "analyze_etymology")
        workflow.add_edge("analyze_etymology", "generate_candidates")
        workflow.add_edge("generate_candidates", "arbitrate")
        workflow.add_edge("arbitrate", "persist_and_render")
        workflow.add_edge("persist_and_render", END)

        return workflow.compile()

    def _extract_terms(self, state: OrchestratorState) -> OrchestratorState:
        terms = extract_candidate_terms(state["raw_text"])
        if not terms:
            terms = ["unknown_term"]
        return {"terms": terms, "unknown_only": terms == ["unknown_term"]}

    def _analyze_etymology(self, state: OrchestratorState) -> OrchestratorState:
        if state.get("unknown_only"):
            return {"etym_reports": []}
        etym_reports: list[dict[str, str]] = []
        for term in state["terms"]:
            etym_report = analyze_etymology(term=term, context=state["raw_text"], provider="gemini")
            etym_reports.append(etym_report)
        return {"etym_reports": etym_reports}

    def _generate_candidates(self, state: OrchestratorState) -> OrchestratorState:
        if state.get("unknown_only"):
            return {"candidate_pool": []}
        candidate_pool: list[dict[str, Any]] = []
        for term in state["terms"]:
            generated = generate_candidates(term)
            for key, value in generated.items():
                if isinstance(value, dict):
                    provider = str(value.get("provider", key))
                    text = str(value.get("text", ""))
                    latency_ms = float(value.get("latency_ms", 0.0) or 0.0)
                    error = value.get("error")
                else:
                    provider = str(key)
                    text = str(value)
                    latency_ms = 0.0
                    error = None
                final = compute_final_score(
                    mqm_score=0.9,
                    context_score=0.9,
                    frequency_score=0.9,
                )
                candidate_pool.append(
                    {
                        "term": term,
                        "source": key,
                        "provider": provider,
                        "text": text,
                        "latency_ms": latency_ms,
                        "error": error,
                        "final": final,
                    }
                )
        return {"candidate_pool": candidate_pool}

    def _arbitrate(self, state: OrchestratorState) -> OrchestratorState:
        if state.get("unknown_only"):
            return {
                "consensus": {
                    "status": "fallback",
                    "winner": "unknown_term",
                    "final": 0.0,
                }
            }
        consensus = select_consensus(
            candidates=state["candidate_pool"],
            threshold=0.9,
            kanji_raw=state["raw_text"],
            romaji="",
        )
        return {"consensus": consensus}

    def _persist_and_render(self, state: OrchestratorState) -> OrchestratorState:
        return {}

    async def run(self, raw_text: str, source_declaration: str) -> dict[str, Any]:
        initial_state: OrchestratorState = {
            "raw_text": raw_text,
            "source_declaration": source_declaration,
            "terms": [],
            "etym_reports": [],
            "candidate_pool": [],
        }
        final_state = await self._app.ainvoke(initial_state)
        return dict(final_state)
