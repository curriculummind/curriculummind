"""
General-knowledge answerability classification (Decision 033).

Retrieval finding "low" confidence (no curriculum evidence judged
actually relevant, Decision 016) doesn't by itself mean the question
was a bad one -- a Grade 6 student asking "what is a decimal" mid a
decimal-*operations* lesson is asking something completely legitimate
that the ingested curriculum text simply never defines, because it
assumes that was taught an earlier grade. Confirmed live: every scope
(the selected topic, its whole concept, the entire subject corpus)
retrieves only operations content for that question, and the relevance
judge correctly rejects all of it -- this isn't a retrieval bug.

This one extra classification call, run only on that terminal
low-confidence path, separates "a real concept for this subject and
grade that we just don't have material on" from "actually unrelated to
the subject, nonsensical, or not a real concept" -- the former gets a
clearly-labeled general-knowledge explanation instead of a flat
refusal (`generate_general_knowledge_response`,
`app/tutoring/generation.py`); the latter still declines.
"""

from pydantic import BaseModel

from app.providers.llm import LLMClient, Message

CLASSIFICATION_PROMPT = """A Grade {grade_band} student studying {subject} asked: {question}

The curriculum materials for this course don't cover this specific question.
Is this nonetheless a genuine {subject} concept appropriate to explain to a
student at this grade level -- including prerequisite material that would
normally have been taught in an earlier grade, or a term/idea closely
related to what this course covers?

Answer no if the question is unrelated to {subject} entirely, nonsensical,
or not a real concept at all -- not just because this specific course
doesn't happen to cover it."""


class GeneralKnowledgeAnswerability(BaseModel):
    """Whether an out-of-corpus question is still a legitimate subject concept worth explaining."""

    can_answer: bool


async def classify_answerable_generally(question: str, subject: str, grade_band: str, llm: LLMClient) -> bool:
    """Classify whether a question with no curriculum evidence is still a legitimate concept to explain."""
    prompt = CLASSIFICATION_PROMPT.format(question=question, subject=subject, grade_band=grade_band)
    classification = await llm.generate_structured(
        [Message(role="user", content=prompt)], GeneralKnowledgeAnswerability
    )
    return classification.can_answer
