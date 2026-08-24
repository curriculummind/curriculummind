"""
Minimal grounded response generation for the M0 slice.

Composes a prompt from retrieved curriculum evidence and streams a
direct explanation back. Strategy selection, assignment-sensitive
behavior, and hint progression (architecture §10-§11) are not built yet
-- this always explains directly, grade-appropriately. Full pedagogical
branching is M1 work.
"""

from collections.abc import AsyncIterator

from app.providers.llm import LLMClient, Message
from app.retrieval.models import RetrievedChunk

SYSTEM_PROMPT = """You are CurriculumMind, a tutor for a Grade {grade_band} student studying {subject}.

Answer using only the curriculum evidence provided below. Explain clearly and
concretely for this grade level. If the evidence doesn't fully answer the
question, say what it does cover rather than inventing beyond it. Do not
mention "evidence", "chunks", or that you were given source material --
just teach the student directly, as a tutor would."""


def _format_evidence(evidence: list[RetrievedChunk]) -> str:
    """Render retrieved chunks as a labeled block for the generation prompt."""
    blocks = [f"[Source: {chunk.resource_title}]\n{chunk.content}" for chunk in evidence]
    return "\n\n---\n\n".join(blocks)


async def generate_grounded_response(
    question: str,
    evidence: list[RetrievedChunk],
    *,
    subject: str,
    grade_band: str,
    llm: LLMClient,
) -> AsyncIterator[str]:
    """Stream a direct, grade-appropriate explanation grounded in evidence."""
    system = SYSTEM_PROMPT.format(grade_band=grade_band, subject=subject)
    user_message = f"Curriculum evidence:\n\n{_format_evidence(evidence)}\n\nStudent question: {question}"
    async for token in llm.generate_text([Message(role="user", content=user_message)], system=system):
        yield token
