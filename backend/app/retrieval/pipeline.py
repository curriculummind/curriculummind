"""
Retrieval pipeline entrypoint: embed the student's question, run the
metadata-filtered vector search, and score confidence. This is the
synchronous portion of the tutoring pipeline that runs before strategy
selection and generation (architecture §8).
"""

from psycopg_pool import AsyncConnectionPool

from app.providers.embeddings import EmbeddingClient
from app.retrieval.confidence import score_retrieval_confidence
from app.retrieval.models import ConfidenceResult
from app.retrieval.store import search_chunks


async def retrieve(
    question: str,
    *,
    subject_slug: str,
    grade_band: str,
    embedder: EmbeddingClient,
    pool: AsyncConnectionPool,
    concept_slug: str | None = None,
) -> ConfidenceResult:
    """Run the full retrieve-then-score step for one student question."""
    [query_embedding] = await embedder.embed([question])
    candidates = await search_chunks(
        pool,
        query_embedding,
        subject_slug=subject_slug,
        grade_band=grade_band,
        concept_slug=concept_slug,
    )
    return score_retrieval_confidence(candidates)
