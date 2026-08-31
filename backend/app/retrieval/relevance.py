"""
LLM-based relevance judgment (Decision 016, extended by Pillar D to run
on every turn rather than only low-confidence ones).

Raw cosine similarity alone cannot reliably separate on-topic from
off-topic queries on a corpus this size, in either direction: a
genuinely on-topic, single-concept query ("what is a ribosome") can
score lower than a genuinely off-topic one whose phrasing happens to
overlap lexically with the corpus (a baking question scoring above a
WWII-date question, because the ratios content uses recipe examples) --
and a short, numeric-only follow-up answer deep in a real conversation
("3", "8:4") can score confidently high against completely unrelated
content, since it carries no topic keywords of its own. One extra
classification call, run on every turn, resolves cases a pure
threshold cannot catch in either direction.

The judgment prompt itself was too literal about phrasing at first: the
same passage, containing an explicit worked "2:3" ratio example, was
judged relevant to "what does 2:3 mean" but not to "what is 2:3" --
the model read "what is" as a request to compute a value rather than
explain notation. Reworded to ask about the underlying concept, not a
literal text match, so a passage teaching ratio notation in general
counts as relevant to a question about a specific ratio's notation
even when the exact numbers differ.
"""

from pydantic import BaseModel

from app.providers.llm import LLMClient, Message
from app.retrieval.models import RetrievedChunk


class RelevanceJudgment(BaseModel):
    """Whether a retrieved passage can actually answer the student's question."""

    can_answer: bool


async def is_actually_relevant(question: str, top_chunk: RetrievedChunk, llm: LLMClient) -> bool:
    """Ask the model directly whether the top candidate can help teach what the question is really about."""
    prompt = (
        f"A Grade 6 student asked or said: {question}\n\n"
        f"Retrieved curriculum passage:\n{top_chunk.content}\n\n"
        "Could a tutor use this passage to teach the underlying concept the student needs, "
        "even if the passage doesn't use the exact same numbers or wording? Judge the "
        "concept being asked about, not a literal text match -- a passage teaching ratio "
        "notation in general is relevant to a question about what a specific ratio like "
        "\"2:3\" means, even if \"2:3\" isn't the exact example used in the passage."
    )
    judgment = await llm.generate_structured([Message(role="user", content=prompt)], RelevanceJudgment)
    return judgment.can_answer
