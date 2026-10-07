"""
Context precision: of the chunks retrieval actually returned, what
fraction are genuinely usable to answer the question.

Deliberately reuses `is_actually_relevant` (`app/retrieval/relevance.py`)
rather than writing a second, parallel relevance judgment -- it's
already the exact question this metric asks, already tested, and
already proven on this corpus's hard cases (Decision 016).

`judge_relevance` is split out from `score_context_precision` because
the runner needs the same per-chunk judgments for a second purpose: the
live pipeline's confidence band isn't just `retrieve()`'s raw similarity
gate, it's that gate *overridden by this exact relevance check*
(`_relevance_check_node`, `app/tutoring/graph.py`) -- a raw-similarity
"high" band with zero chunks the model judges actually relevant is a
"low" band in production. Scoring precision and determining the
effective band from two separate calls to the LLM would double the
judgment cost for no benefit; sharing one set of judgments avoids that.
"""

import asyncio

from app.providers.llm import LLMClient
from app.retrieval.models import RetrievedChunk
from app.retrieval.relevance import is_actually_relevant


async def judge_relevance(question: str, evidence: list[RetrievedChunk], llm: LLMClient) -> list[bool]:
    """One relevance judgment per chunk, in the same order as `evidence`. Empty list on empty evidence."""
    if not evidence:
        return []
    return list(await asyncio.gather(*(is_actually_relevant(question, chunk, llm) for chunk in evidence)))


async def score_context_precision(question: str, evidence: list[RetrievedChunk], llm: LLMClient) -> float:
    """Fraction of retrieved chunks judged usable to answer the question. 0.0 on empty evidence."""
    judgments = await judge_relevance(question, evidence, llm)
    if not judgments:
        return 0.0
    return sum(judgments) / len(judgments)
