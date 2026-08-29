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
"""

from pydantic import BaseModel

from app.providers.llm import LLMClient, Message
from app.retrieval.models import RetrievedChunk


class RelevanceJudgment(BaseModel):
    """Whether a retrieved passage can actually answer the student's question."""

    can_answer: bool


async def is_actually_relevant(question: str, top_chunk: RetrievedChunk, llm: LLMClient) -> bool:
    """Ask the model directly whether the top candidate answers the question."""
    prompt = (
        f"Student question: {question}\n\n"
        f"Retrieved passage:\n{top_chunk.content}\n\n"
        "Does this passage contain enough information to answer the student's "
        "question, even partially? Judge based only on the passage's actual "
        "content, not on how related the topic sounds."
    )
    judgment = await llm.generate_structured([Message(role="user", content=prompt)], RelevanceJudgment)
    return judgment.can_answer
