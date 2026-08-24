"""Unit tests for retrieval confidence scoring."""

from app.retrieval.confidence import score_retrieval_confidence
from app.retrieval.models import RetrievedChunk


def _chunk(similarity: float) -> RetrievedChunk:
    return RetrievedChunk(
        chunk_id="00000000-0000-0000-0000-000000000000",
        resource_title="Test Resource",
        source_url="https://example.com",
        license="test",
        content="test content",
        similarity=similarity,
    )


def test_empty_candidates_are_low_confidence() -> None:
    """No candidates at all should never be treated as high confidence."""
    result = score_retrieval_confidence([])
    assert result.band == "low"
    assert result.evidence == []


def test_strong_top_match_is_high_confidence() -> None:
    """A top match above the threshold is high confidence."""
    result = score_retrieval_confidence([_chunk(0.6), _chunk(0.4)])
    assert result.band == "high"


def test_weak_top_match_is_low_confidence() -> None:
    """A top match below the threshold is low confidence."""
    result = score_retrieval_confidence([_chunk(0.1), _chunk(0.05)])
    assert result.band == "low"


def test_clustered_high_scores_are_still_high_confidence() -> None:
    """Multiple close, strong scores should not be penalized as ambiguous."""
    result = score_retrieval_confidence([_chunk(0.62), _chunk(0.61), _chunk(0.60)])
    assert result.band == "high"
