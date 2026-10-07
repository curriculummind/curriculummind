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

A third case (Decision 035), checked first: the question isn't
chunk-grounded, but it's still genuinely about a topic *this course*
teaches -- not a different, earlier-grade prerequisite, the actual
subject matter ("why do we need decimals when we have ratios" under a
course that covers both). `classify_topic_in_scope` judges this
directly against the real list of topic names this subject/grade
covers (`get_concept_names`, `app/retrieval/store.py`), not a generic
"is this a legitimate concept somewhere" question -- that's what
`classify_answerable_generally` above already asks, for the case where
it genuinely isn't one of this course's own topics. When a question
matches a real topic directly, there's no need to also ask the more
generic question, saving a call on what's the more common of the two.
"""

from pydantic import BaseModel

from app.providers.llm import LLMClient, Message

TOPIC_SCOPE_PROMPT = """A Grade {grade_band} student studying {subject} asked: {question}

This course covers these topics:
{topics}

Does the question fall under one of these topics, even if it's asking for more
depth, a comparison, or a different angle than whatever specific passage was
retrieved -- not necessarily word-for-word one of the names above, but
genuinely about one of them?

Answer no if the question isn't really about any of these topics, even if
it's a real concept in {subject} generally."""


class TopicScopeJudgment(BaseModel):
    """Whether a question is genuinely about one of this course's own topics."""

    in_scope: bool


async def classify_topic_in_scope(
    question: str, topics: list[str], subject: str, grade_band: str, llm: LLMClient
) -> bool:
    """Classify whether a question is genuinely about a topic this specific course covers."""
    prompt = TOPIC_SCOPE_PROMPT.format(
        question=question, subject=subject, grade_band=grade_band, topics="\n".join(f"- {t}" for t in topics)
    )
    judgment = await llm.generate_structured([Message(role="user", content=prompt)], TopicScopeJudgment)
    return judgment.in_scope


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
