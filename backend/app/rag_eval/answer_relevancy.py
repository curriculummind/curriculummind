"""
Answer relevancy: does the answer actually address what was asked, as
opposed to being faithful-but-off-topic (e.g. correctly grounded in the
evidence, but answering a narrower or broader question than the
student's).

Unlike the other three metrics, this one keeps RAGAS's own published
method unchanged rather than substituting an LLM judgment for it: ask
the model for several questions the answer would be a good response to,
embed those alongside the original question, and score by how close
they land. This stack already has the embedding client the method
needs (`EmbeddingClient`, used at ingestion and query time), so there's
no mismatch to design around here the way there was for the other
metrics' LangChain-shaped originals.
"""

import math

from pydantic import BaseModel

from app.providers.embeddings import EmbeddingClient
from app.providers.llm import LLMClient, Message

_GENERATED_QUESTION_COUNT = 3


class GeneratedQuestions(BaseModel):
    """Questions that the given answer would be a good, direct response to."""

    questions: list[str]


def _cosine_similarity(a: list[float], b: list[float]) -> float:
    dot = sum(x * y for x, y in zip(a, b, strict=True))
    norm_a = math.sqrt(sum(x * x for x in a))
    norm_b = math.sqrt(sum(y * y for y in b))
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return dot / (norm_a * norm_b)


async def score_answer_relevancy(question: str, answer: str, llm: LLMClient, embedder: EmbeddingClient) -> float:
    """Mean cosine similarity between the original question and questions reverse-engineered from the answer."""
    prompt = (
        f"A tutor gave this response:\n\n{answer}\n\n"
        f"Write exactly {_GENERATED_QUESTION_COUNT} different questions that this response would be a good, "
        "direct answer to. If the response is incomplete or evasive, write questions that reflect what it "
        "actually addresses, not what it should have addressed."
    )
    generated = await llm.generate_structured([Message(role="user", content=prompt)], GeneratedQuestions)
    if not generated.questions:
        return 0.0
    embeddings = await embedder.embed([question, *generated.questions])
    question_embedding, generated_embeddings = embeddings[0], embeddings[1:]
    similarities = [_cosine_similarity(question_embedding, candidate) for candidate in generated_embeddings]
    return sum(similarities) / len(similarities)
