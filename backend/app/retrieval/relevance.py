"""
LLM-based relevance judgment, used when similarity-based confidence is
low (architecture §16's broaden-or-clarify branch).

Raw cosine similarity alone cannot reliably separate on-topic from
off-topic queries on a corpus this size: a genuinely on-topic,
single-concept query ("what is a ribosome") can score lower than a
genuinely off-topic one whose phrasing happens to overlap lexically
with the corpus (a baking question scoring above a WWII-date question,
because the ratios content uses recipe examples). One extra
classification call resolves cases a pure threshold cannot.
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
