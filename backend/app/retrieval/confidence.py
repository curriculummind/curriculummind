"""Retrieval confidence scoring and fallback branching (architecture §16)."""

from app.retrieval.models import ConfidenceResult, RetrievedChunk

# Calibrated empirically against the seed corpus with text-embedding-3-small:
# on-topic questions scored 0.38-0.62 cosine similarity against their best
# chunk, off-topic questions scored 0.07-0.23. 0.32 sits with margin above
# the observed off-topic ceiling and below the observed on-topic floor.
# Revisit once the offline evaluation harness (architecture §22) has more
# data than these six manual probes.
HIGH_CONFIDENCE_SIMILARITY = 0.32


def score_retrieval_confidence(candidates: list[RetrievedChunk]) -> ConfidenceResult:
    """
    Score confidence in a retrieval result set using top-match similarity.

    Returns a "low" band (triggering the broaden/clarify branch) if the
    top match is too weak to trust. A small gap between the top result
    and the runner-up is *not* treated as a low-confidence signal --
    multiple chunks from the same resource legitimately cluster together
    when a query is well covered by the corpus.
    """
    if not candidates:
        return ConfidenceResult(band="low", evidence=[])

    band = "high" if candidates[0].similarity >= HIGH_CONFIDENCE_SIMILARITY else "low"
    return ConfidenceResult(band=band, evidence=candidates)
