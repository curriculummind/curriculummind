"""
Context recall: of the facts a correct answer needs, how many does the
retrieved evidence actually contain. Unlike context precision (which
judges each chunk in isolation), this judges the whole retrieved set
against a hand-written list of atomic facts the golden case expects --
so it catches a retrieval that found several *topically* relevant but
redundant chunks while missing the one fact the question actually needs.
"""

from pydantic import BaseModel

from app.providers.llm import LLMClient, Message
from app.retrieval.models import RetrievedChunk


class FactCoverage(BaseModel):
    """Whether each reference fact, in the same order given, is supported by the evidence."""

    present: list[bool]


async def score_context_recall(reference_facts: list[str], evidence: list[RetrievedChunk], llm: LLMClient) -> float:
    """Fraction of reference_facts the retrieved evidence collectively supports. 0.0 on empty evidence."""
    if not evidence or not reference_facts:
        return 0.0
    evidence_text = "\n\n---\n\n".join(chunk.content for chunk in evidence)
    facts_text = "\n".join(f"{i + 1}. {fact}" for i, fact in enumerate(reference_facts))
    prompt = (
        f"Retrieved curriculum passages:\n\n{evidence_text}\n\n"
        f"Candidate facts a complete answer should cover:\n{facts_text}\n\n"
        "For each numbered fact, in order, is it actually stated or directly supported "
        "somewhere in the retrieved passages above? Judge what the passages actually say, "
        "not what a Grade 6 student would already know or what seems generally true."
    )
    coverage = await llm.generate_structured([Message(role="user", content=prompt)], FactCoverage)
    if len(coverage.present) != len(reference_facts):
        return sum(coverage.present) / max(len(coverage.present), 1)
    return sum(coverage.present) / len(reference_facts)
