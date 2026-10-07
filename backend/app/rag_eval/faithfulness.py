"""
Faithfulness: of the concrete claims the generated answer makes, how
many actually follow from the retrieved evidence, rather than from the
model's own general knowledge.

RAGAS's published method splits this into two calls: decompose the
answer into atomic claims, then verify each against the context
separately. Combined into one call here -- a deliberate simplification,
not an oversight -- since both steps are judging the same two texts
(answer, evidence) and halving the per-case call count matters for a
harness meant to be re-run after every retrieval/prompt change.
"""

from pydantic import BaseModel

from app.providers.llm import LLMClient, Message
from app.retrieval.models import RetrievedChunk


class ClaimJudgment(BaseModel):
    """One atomic factual claim extracted from the answer, and whether the evidence supports it."""

    text: str
    supported: bool


class Claims(BaseModel):
    """Every atomic factual claim the answer makes, each judged against the evidence."""

    claims: list[ClaimJudgment]


async def score_faithfulness(answer: str, evidence: list[RetrievedChunk], llm: LLMClient) -> float:
    """
    Fraction of the answer's atomic claims that are supported by the
    evidence. 1.0 if the answer makes no checkable factual claims (e.g.
    it's purely a question back to the student).
    """
    evidence_text = "\n\n---\n\n".join(chunk.content for chunk in evidence)
    prompt = (
        f"A tutor gave this response to a student:\n\n{answer}\n\n"
        f"Curriculum evidence the tutor was given to ground the response in:\n\n{evidence_text}\n\n"
        "Break the tutor's response down into its individual atomic factual claims -- each "
        "one independently checkable statement, not a question or instruction to the student. "
        "For each claim, judge whether it's actually stated or directly implied by the evidence "
        "above, not whether it's true in general or something a tutor could reasonably know."
    )
    result = await llm.generate_structured([Message(role="user", content=prompt)], Claims)
    if not result.claims:
        return 1.0
    return sum(claim.supported for claim in result.claims) / len(result.claims)
