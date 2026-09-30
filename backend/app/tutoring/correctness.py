"""
Answer correctness classification (Decision 019).

A single structured classification call, same shape as the relevance
judgment (Decision 016) and assignment detection (Decision 017), that
judges a student's answer against the tutor's most recent guiding or
confirm question. This replaces inferring correctness implicitly inside
the generation call by re-reading the raw transcript -- a fragile
approach that had already produced a real misjudgment (a guided-
discovery thread losing track of whether "4" was a correct answer).
The classification itself doesn't change the response; the router uses
it to update a conversation's struggle/confirm counters and choose a
generation strategy.
"""

import re
from typing import Literal

from pydantic import BaseModel

from app.providers.llm import LLMClient, Message

_BLANK_LINE = re.compile(r"\n\s*\n")

CLASSIFICATION_PROMPT = """A tutor said this to a student:

{tutor_message}

The specific question to judge the student's answer against is:

{tutor_question}

(Use the rest of the tutor's message above only to understand what that
question refers to -- e.g. what "that ratio" or "it" means -- not as a
separate thing to also judge the answer against.)

The student answered:

{student_answer}

Judge the student's answer against that specific question:
- "correct" if the answer is right, or close enough to show real understanding.
  If the question invites an attempt ("can you find...", "what would you
  get...", "do you see a way..."), a direct answer attempting it counts as
  engaging with the question even without a preceding "yes" -- judge the
  content of the attempt, not whether the student verbally confirmed first.
- "incorrect" if the answer is wrong or shows a clear misunderstanding.
- "unclear" if the answer doesn't actually engage with the question (e.g. a
  side question, "I don't know", or something unrelated) -- not a wrong
  attempt, just not an attempt to judge."""


class AnswerCorrectness(BaseModel):
    """Whether a student's answer to the tutor's last question was correct."""

    status: Literal["correct", "incorrect", "unclear"]


def _last_question(assistant_message: str) -> str:
    """
    Isolate the trailing question from a guided-discovery response.

    The generation prompts (Decision 015) always separate a stated
    anchor from the genuine follow-up question with a blank line.
    Passing the whole anchor+question blob as "the tutor's question"
    confuses the classifier -- worked-example numbers in the anchor can
    read as part of the question being judged. Mirrors the same split
    the frontend does for display (splitAnchorAndPrompt).
    """
    parts = _BLANK_LINE.split(assistant_message.strip())
    last = parts[-1].strip()
    if len(parts) > 1 and last.endswith("?"):
        return last
    return assistant_message


async def classify_answer(tutor_message: str, student_answer: str, llm: LLMClient) -> str:
    """
    Classify a student's answer against the tutor's last question as
    correct/incorrect/unclear.

    Passes the full tutor_message (anchor + question) alongside the
    isolated question, not the isolated question alone: a follow-up
    question routinely refers back to the anchor ("that ratio", "it"),
    and the classifier can't judge an answer against a reference it
    can't resolve. Isolating the question is still necessary -- without
    it, worked-example numbers in the anchor read as part of the
    question being judged -- just not sufficient on its own.
    """
    prompt = CLASSIFICATION_PROMPT.format(
        tutor_message=tutor_message, tutor_question=_last_question(tutor_message), student_answer=student_answer
    )
    classification = await llm.generate_structured([Message(role="user", content=prompt)], AnswerCorrectness)
    return classification.status
