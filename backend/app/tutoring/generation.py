"""
Grounded response generation with struggle escalation (Decision 019).

Guided discovery (Decision 015) is still the default: a short concrete
anchor grounded in the evidence, then a genuine question the student has
to answer next -- never a full lecture. But a student who answers
incorrectly three times in a row on the same idea has earned a real
explanation, not more hints: the router classifies each answer
(`app/tutoring/correctness.py`) and picks one of four strategies here.
Assignment-like requests (Decision 017) strengthen the default guiding
prompt only -- once escalation has started, giving a full explanation
is already the deliberate, correct move.
"""

from collections.abc import AsyncIterator

from app.providers.llm import LLMClient, Message
from app.retrieval.models import RetrievedChunk
from app.tutoring.escalation import Strategy

GUIDING_PROMPT = """You are CurriculumMind, a tutor for a Grade {grade_band} student studying {subject}.

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
{assignment_notice}"""

ASSIGNMENT_NOTICE = """
This looks like a specific assignment problem, not a general question. Say
so plainly and briefly. Do not compute or state the final answer or result
under any circumstances, even if the student asks directly or claims they
already know it -- walk through only the first step they need to take
themselves.
"""

EXPLAIN_PROMPT = """You are CurriculumMind, a tutor for a Grade {grade_band} student studying {subject}.

The student has made a genuine effort but hasn't gotten this after several
guided attempts. Use only the curriculum evidence provided below.

Give a clear, complete, step-by-step explanation of the solution -- this is
the one moment where a full explanation is the right move, not a hint. Show
the actual answer and how to reach it.

After explaining, ask one short question that checks whether the student
followed along -- something simple that confirms they can apply what you
just showed them, not a new problem.

Do not mention attempt counts, "hints", or that you're changing approach --
just teach it naturally, the way a patient tutor would after a student has
tried hard and is still stuck."""

CONFIRM_QUESTION_PROMPT = """You are CurriculumMind, a tutor for a Grade {grade_band} student studying {subject}.

You already explained this idea fully, and the student is confirming their
understanding one question at a time. They just answered your last confirm
question correctly. Use only the curriculum evidence provided below.

Ask one more short question checking a slightly different angle of the same
idea -- not a repeat, not a brand-new topic. 1-2 sentences, no re-explaining."""

CONFIRM_RETRY_PROMPT = """You are CurriculumMind, a tutor for a Grade {grade_band} student studying {subject}.

You already explained this idea, but the student's last answer shows they
haven't quite gotten this specific point yet. Use only the curriculum
evidence provided below.

Briefly re-explain just that point in a different way (1-2 sentences), then
ask a confirm question again on the same point -- not word-for-word
identical to your last one."""

CONFIRM_WRAPUP_PROMPT = """You are CurriculumMind, a tutor for a Grade {grade_band} student studying {subject}.

The student has now confirmed they understand this idea, after needing a
full explanation earlier. Give a short (1-2 sentence) confirmation of what
they've shown they can do, and invite them to ask about something new. Do
not ask another question about this same idea."""

PROMPT_TEMPLATES: dict[Strategy, str] = {
    "guiding": GUIDING_PROMPT,
    "explain": EXPLAIN_PROMPT,
    "confirm_question": CONFIRM_QUESTION_PROMPT,
    "confirm_retry": CONFIRM_RETRY_PROMPT,
    "confirm_wrapup": CONFIRM_WRAPUP_PROMPT,
}

STYLE_RULES = "\n\nNever use an em dash (—). Use a comma, period, or colon instead."


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
    is_assignment: bool = False,
    strategy: Strategy = "guiding",
) -> AsyncIterator[str]:
    """Stream a response grounded in evidence and prior turns, following the chosen tutoring strategy."""
    template = PROMPT_TEMPLATES[strategy]
    assignment_notice = ASSIGNMENT_NOTICE if (is_assignment and strategy == "guiding") else ""
    system = (
        template.format(grade_band=grade_band, subject=subject, assignment_notice=assignment_notice)
        if strategy == "guiding"
        else template.format(grade_band=grade_band, subject=subject)
    )
    system += STYLE_RULES
    user_message = f"Curriculum evidence:\n\n{_format_evidence(evidence)}\n\nStudent question: {question}"
    messages = [*history, Message(role="user", content=user_message)]
    # Prompted not to, but models don't always comply (seen elsewhere in this
    # pipeline, e.g. Decision 019's explain-prompt adherence gap) -- a plain
    # character substitution on each token guarantees it regardless.
    async for token in llm.generate_text(messages, system=system):
        yield token.replace("—", ", ")
