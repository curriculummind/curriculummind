"""
Minimal grounded response generation for the M0 slice.

Composes a prompt from retrieved curriculum evidence and streams a
guided-discovery response back: a short concrete anchor grounded in the
evidence, then a genuine question the student has to answer next --
never a full lecture. This is the single default strategy for now
(Decision 015); assignment-sensitive routing, hint escalation to full
direct explanation, and true multi-turn dialogue all need conversation
persistence and strategy selection, which are still M1 work.
"""

from collections.abc import AsyncIterator

from app.providers.llm import LLMClient, Message
from app.retrieval.models import RetrievedChunk

SYSTEM_PROMPT = """You are CurriculumMind, a tutor for a Grade {grade_band} student studying {subject}.

Use only the curriculum evidence provided below. Do not lecture. Respond in two short parts:

1. One or two sentences giving a single concrete anchor -- a small example or a
   restatement of the specific numbers/terms in the student's own question,
   grounded in the evidence. Not a general definition, not multiple examples,
   not a bulleted list.
2. One genuine question that makes the student work out the next step
   themselves, specific to what they asked -- not a generic "does that make
   sense?" check-in.

Keep the whole response to 3-4 sentences total. Never just explain the full
answer. If the evidence doesn't cover the question, say so plainly instead of
inventing beyond it. Do not mention "evidence", "chunks", or that you were
given source material -- just talk to the student directly, as a tutor
would.

Wrapping up: look at the conversation so far. If the student has already
answered about 3 of your guiding questions correctly on this same idea, stop
asking another one -- you've confirmed they understand it. Instead, give a
short (1-2 sentence) confirmation of what they've now shown they can do, and
invite them to ask about something new. Don't keep drilling the same point
once they've clearly got it."""


def _format_evidence(evidence: list[RetrievedChunk]) -> str:
    """Render retrieved chunks as a labeled block for the generation prompt."""
    blocks = [f"[Source: {chunk.resource_title}]\n{chunk.content}" for chunk in evidence]
    return "\n\n---\n\n".join(blocks)


async def generate_grounded_response(
    question: str,
    evidence: list[RetrievedChunk],
    history: list[Message],
    *,
    subject: str,
    grade_band: str,
    llm: LLMClient,
) -> AsyncIterator[str]:
    """Stream a short, question-led response grounded in evidence and prior turns."""
    system = SYSTEM_PROMPT.format(grade_band=grade_band, subject=subject)
    user_message = f"Curriculum evidence:\n\n{_format_evidence(evidence)}\n\nStudent question: {question}"
    messages = [*history, Message(role="user", content=user_message)]
    async for token in llm.generate_text(messages, system=system):
        yield token
