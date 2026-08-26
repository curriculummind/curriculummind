"""
Tutoring decision graph (Decision 006, adopted).

A LangGraph StateGraph replacing the hand-written asyncio.gather/if-else
chain that used to live in the router: a content-safety check gates the
entry point (Decision 022, the "safety check" node named in Decision
006 but never built until now), then retrieval and assignment detection
run as parallel nodes, a conditional edge routes low-confidence results
through the relevance fallback (Decision 016), and another classifies
the student's last answer (Decision 019) before a final node decides
the generation strategy. Every node wraps an existing, already-tested
module (retrieval/, assignment.py, correctness.py, escalation.py,
safety.py) unchanged -- this only changes how they are orchestrated,
not what any of them do.

Generation itself (streaming tokens back to the client) deliberately
stays outside the graph and runs in the router after it completes: a
single `ainvoke` call returns one final state, which doesn't fit a
token-streaming response cleanly. The graph's job ends at "here is the
evidence, the assignment flag, and the strategy to generate with" --
exactly the point Principle 5 draws between deciding and generating.
"""

from typing import TypedDict

from langgraph.graph import END, StateGraph

from app.db import get_pool
from app.providers.embeddings import EmbeddingClient
from app.providers.llm import LLMClient, Message
from app.retrieval.models import RetrievedChunk
from app.retrieval.pipeline import retrieve
from app.retrieval.relevance import is_actually_relevant
from app.tutoring.assignment import detect_assignment
from app.tutoring.correctness import classify_answer
from app.tutoring.escalation import next_state
from app.tutoring.safety import classify_safety, should_block


class TutoringState(TypedDict, total=False):
    """Shared state threaded through the tutoring decision graph."""

    question: str
    retrieval_query: str
    subject: str
    grade_band: str
    history: list[Message]
    llm: LLMClient
    embedder: EmbeddingClient
    tutoring_phase: str
    struggle_count: int
    confirm_count: int

    safety_category: str
    safety_blocked: bool

    band: str
    evidence: list[RetrievedChunk]
    is_assignment: bool
    correctness: str | None
    strategy: str
    new_phase: str
    new_struggle_count: int
    new_confirm_count: int


async def _check_safety_node(state: TutoringState) -> dict:
    """Classify the raw question for content-safety concerns (Decision 022) before anything else runs."""
    category = await classify_safety(state["question"], state["llm"])
    return {"safety_category": category, "safety_blocked": should_block(category)}


async def _retrieve_node(state: TutoringState) -> dict:
    """Run curriculum retrieval with its built-in similarity confidence gate."""
    result = await retrieve(
        state["retrieval_query"],
        subject_slug=state["subject"],
        grade_band=state["grade_band"],
        embedder=state["embedder"],
        pool=get_pool(),
    )
    return {"band": result.band, "evidence": result.evidence}


async def _detect_assignment_node(state: TutoringState) -> dict:
    """Classify whether the question reads like a pasted assignment problem."""
    is_assignment = await detect_assignment(state["question"], state["llm"])
    return {"is_assignment": is_assignment}


async def _relevance_check_node(state: TutoringState) -> dict:
    """On a low-confidence result, ask the model directly whether the top candidate actually answers it."""
    evidence = state.get("evidence") or []
    if evidence and await is_actually_relevant(state["question"], evidence[0], state["llm"]):
        return {"band": "high"}
    return {}


async def _classify_correctness_node(state: TutoringState) -> dict:
    """Classify the student's answer against the tutor's last question, if there was one."""
    last_assistant_message = next(
        (message for message in reversed(state["history"]) if message.role == "assistant"), None
    )
    if last_assistant_message is None:
        return {"correctness": None}
    correctness = await classify_answer(last_assistant_message.content, state["question"], state["llm"])
    return {"correctness": correctness}


def _select_strategy_node(state: TutoringState) -> dict:
    """Turn the correctness judgment and current tutoring state into a generation strategy."""
    correctness = state.get("correctness")
    if correctness is None:
        return {
            "strategy": "guiding",
            "new_phase": state["tutoring_phase"],
            "new_struggle_count": state["struggle_count"],
            "new_confirm_count": state["confirm_count"],
        }
    outcome = next_state(state["tutoring_phase"], state["struggle_count"], state["confirm_count"], correctness)
    return {
        "strategy": outcome.strategy,
        "new_phase": outcome.phase,
        "new_struggle_count": outcome.struggle_count,
        "new_confirm_count": outcome.confirm_count,
    }


def _route_after_safety(state: TutoringState) -> str | list[str]:
    return END if state["safety_blocked"] else ["retrieve", "detect_assignment"]


def _route_after_retrieve(state: TutoringState) -> str:
    return "relevance_check" if state["band"] == "low" else "classify_correctness"


def _route_after_relevance_check(state: TutoringState) -> str:
    return "classify_correctness" if state["band"] == "high" else END


def _build_graph():
    """Build and compile the tutoring decision graph once at import time."""
    graph = StateGraph(TutoringState)

    graph.add_node("check_safety", _check_safety_node)
    graph.add_node("retrieve", _retrieve_node)
    graph.add_node("detect_assignment", _detect_assignment_node)
    graph.add_node("relevance_check", _relevance_check_node)
    graph.add_node("classify_correctness", _classify_correctness_node)
    graph.add_node("select_strategy", _select_strategy_node)

    graph.set_entry_point("check_safety")

    graph.add_conditional_edges("check_safety", _route_after_safety, ["retrieve", "detect_assignment", END])
    graph.add_conditional_edges(
        "retrieve", _route_after_retrieve, ["relevance_check", "classify_correctness"]
    )
    graph.add_conditional_edges("relevance_check", _route_after_relevance_check, ["classify_correctness", END])
    graph.add_edge("detect_assignment", END)
    graph.add_edge("classify_correctness", "select_strategy")
    graph.add_edge("select_strategy", END)

    return graph.compile()


_compiled_graph = _build_graph()


async def run_tutoring_pipeline(
    *,
    question: str,
    retrieval_query: str,
    subject: str,
    grade_band: str,
    history: list[Message],
    llm: LLMClient,
    embedder: EmbeddingClient,
    tutoring_phase: str,
    struggle_count: int,
    confirm_count: int,
) -> TutoringState:
    """Run the tutoring decision graph and return its final state."""
    initial_state: TutoringState = {
        "question": question,
        "retrieval_query": retrieval_query,
        "subject": subject,
        "grade_band": grade_band,
        "history": history,
        "llm": llm,
        "embedder": embedder,
        "tutoring_phase": tutoring_phase,
        "struggle_count": struggle_count,
        "confirm_count": confirm_count,
    }
    return await _compiled_graph.ainvoke(initial_state)
