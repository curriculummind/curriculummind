"""
Assignment-like request detection (Decision 017).

A single structured classification call that flags when a student's
question reads like a specific graded problem pasted in for a direct
answer, rather than a request for conceptual help. The result doesn't
block or reroute the request -- it strengthens the generation prompt's
existing "never give the final answer" instruction so guided discovery
holds even when a student pastes in exact assignment wording.
"""

from pydantic import BaseModel

from app.providers.llm import LLMClient, Message

CLASSIFICATION_PROMPT = """Student input: {question}

Does this look like a specific assignment or homework problem the student
wants solved for them, rather than a request to understand a concept?

Signs it IS an assignment-like request:
- A verbatim or near-verbatim problem statement with specific numbers/values
  to compute, numbered or lettered problem parts, phrases like "solve for",
  "find the value of", "show your work", references to
  homework/assignment/due date/points, or a direct request for "the answer".
- A self-contained word-problem scenario -- a named setting or character
  plus specific numbers, stated as fact rather than asked as the student's
  own question (e.g. "At the store, the ratio of X to Y was 6:8. For every
  8 Y there were 6 X"). This is the most common way students paste in
  assignment text: they copy the setup and never type an actual question,
  or the question got cut off when pasting. The ABSENCE of a question mark
  on a scenario like this is itself a signal, not a reason to say no --
  a student asking their own question phrases it as a question.
- A bare short numeric or short-phrase reply with no other context (e.g.
  just "4", or "12") is NOT itself a fresh assignment paste -- classify
  those as not-assignment; they are answers to a question already being
  asked, not new pasted problems.

Signs it is NOT: a general question about how something works ("what is a
ratio?", "can you explain equivalent ratios?"), a request for an example, or
a made-up practice question the student is using to check their own
understanding, phrased as their own question.

Judge the structure of the input, not the subject matter -- a question about
ratios is not automatically an assignment, but a self-contained scenario
with concrete numbers and no question of the student's own usually is."""


class AssignmentClassification(BaseModel):
    """Whether a student's input reads like a specific assignment problem."""

    is_assignment: bool


async def detect_assignment(question: str, llm: LLMClient) -> bool:
    """Classify whether the student's question reads like a pasted assignment problem."""
    prompt = CLASSIFICATION_PROMPT.format(question=question)
    classification = await llm.generate_structured(
        [Message(role="user", content=prompt)], AssignmentClassification
    )
    return classification.is_assignment
