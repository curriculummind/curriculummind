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
This looks like a specific assignment problem, not a general question. Do
not compute or state the final answer or result under any circumstances,
even if the student asks directly or claims they already know it -- walk
through only the first step they need to take themselves.
"""

# The model was prompted to open by plainly saying this looks like an
# assignment, but didn't always comply (the same "prompted but not
# guaranteed" gap seen elsewhere in this pipeline, e.g. Decision 019's
# explain-prompt adherence). Sent as a deterministic prefix instead of
# leaving the acknowledgment itself up to the model, so it always
# appears, worded exactly as intended, regardless of compliance. The
# behavioral constraint above (never reveal the final answer) stays
# prompted, since it shapes the model's actual guidance, not just an
# opening line.
ASSIGNMENT_ACKNOWLEDGMENT = (
    "This looks like a specific assignment problem. I won't give you the direct solution, "
    "but let's work through it together.\n\n"
)

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

GENERAL_KNOWLEDGE_PROMPT = """You are CurriculumMind, a tutor for a Grade {grade_band} student studying {subject}.

The student asked a real {subject} question, but your curriculum materials
don't cover it -- it's most likely something normally taught in an earlier
grade. Give a short, clear, accurate explanation anyway: 2-3 sentences,
grade-appropriate, no bulleted list, no full lecture. You may end with one
short question or a quick example offer, but don't demand the student answer
before you'll continue.

Do not claim this is from the student's course materials, and do not
mention "evidence" or "curriculum" -- the opening disclosure is already
handled for you, just teach the concept directly after it."""

# Decision 019's explain-prompt adherence gap applies here too: prompting
# the model to disclose this isn't from the curriculum doesn't guarantee
# it will, every time, in the same words. Sent as a deterministic prefix
# instead, the same pattern ASSIGNMENT_ACKNOWLEDGMENT already uses, since
# this disclosure is the one thing Principle 6 actually needs to hold.
GENERAL_KNOWLEDGE_ACKNOWLEDGMENT = (
    "That's not something your course materials cover, but here's a quick explanation:\n\n"
)

# Decision 035: a sibling of GUIDING_PROMPT, not a parameterization of it --
# generate_grounded_response structurally renders an evidence block into
# every call, which would actively mislead the model here (there's no
# literal retrieved passage to be "limited to"). Same two-part shape, same
# 3-4 sentence cap, same assignment-notice mechanism; the only real change
# is the one sentence governing what the model is allowed to draw on.
IN_SCOPE_PROMPT = """You are CurriculumMind, a tutor for a Grade {grade_band} student studying {subject}.

This question is about a topic this course covers, even though it goes beyond
the specific passage on record for it. Answer from your own full knowledge of
the topic -- you are not limited to one retrieved passage here. Do not
lecture. Respond in two short parts:

1. One or two sentences giving a single concrete anchor -- a small example or a
   restatement of the specific numbers/terms in the student's own question.
   Not a general definition, not multiple examples, not a bulleted list.
2. One genuine question that makes the student work out the next step
   themselves, specific to what they asked -- not a generic "does that make
   sense?" check-in.

Keep the whole response to 3-4 sentences total. Never just explain the full
answer. Do not mention "evidence", "chunks", or that you were given source
material -- just talk to the student directly, as a tutor would.
{assignment_notice}"""


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
    if is_assignment and strategy == "guiding":
        yield ASSIGNMENT_ACKNOWLEDGMENT
    # Prompted not to, but models don't always comply (seen elsewhere in this
    # pipeline, e.g. Decision 019's explain-prompt adherence gap) -- a plain
    # character substitution on each token guarantees it regardless.
    async for token in llm.generate_text(messages, system=system):
        yield token.replace("—", ", ")


async def generate_general_knowledge_response(
    question: str,
    history: list[Message],
    *,
    subject: str,
    grade_band: str,
    llm: LLMClient,
) -> AsyncIterator[str]:
    """
    Stream a clearly-labeled, ungrounded explanation for a question with
    no curriculum evidence (Decision 033) -- only called after
    classify_answerable_generally has judged the question a legitimate
    subject concept, not an arbitrary off-topic one.
    """
    system = GENERAL_KNOWLEDGE_PROMPT.format(grade_band=grade_band, subject=subject) + STYLE_RULES
    messages = [*history, Message(role="user", content=question)]
    yield GENERAL_KNOWLEDGE_ACKNOWLEDGMENT
    async for token in llm.generate_text(messages, system=system):
        yield token.replace("—", ", ")


async def generate_in_scope_response(
    question: str,
    history: list[Message],
    *,
    subject: str,
    grade_band: str,
    llm: LLMClient,
    is_assignment: bool = False,
) -> AsyncIterator[str]:
    """
    Stream a full-depth, guided-discovery-style answer for a question
    that isn't chunk-grounded but is genuinely about a topic this course
    covers (Decision 035) -- only called after classify_topic_in_scope
    has confirmed that. No disclosure prefix, unlike
    generate_general_knowledge_response: this is in-scope content, not
    stepping outside the course. Assignment detection (Decision 017)
    still applies on this tier exactly as on the grounded one -- a
    pasted problem that lands here still doesn't get the final answer
    handed over.
    """
    assignment_notice = ASSIGNMENT_NOTICE if is_assignment else ""
    system = (
        IN_SCOPE_PROMPT.format(grade_band=grade_band, subject=subject, assignment_notice=assignment_notice)
        + STYLE_RULES
    )
    messages = [*history, Message(role="user", content=question)]
    if is_assignment:
        yield ASSIGNMENT_ACKNOWLEDGMENT
    async for token in llm.generate_text(messages, system=system):
        yield token.replace("—", ", ")
