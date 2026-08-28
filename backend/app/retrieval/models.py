"""Data shapes passed between the retrieval pipeline's stages."""

from pydantic import BaseModel


class RetrievedChunk(BaseModel):
    """One candidate chunk returned by vector similarity search."""

    chunk_id: str
    resource_title: str
    source_url: str
    license: str
    content: str
    similarity: float
    standard_code: str | None = None
    framework_name: str | None = None


class ConfidenceResult(BaseModel):
    """
    Outcome of scoring a retrieval candidate set.

    band "high" means the pipeline should proceed to strategy selection
    using `evidence`. band "low" means the confidence gate should trigger
    the broaden-or-clarify branch instead. See architecture §16.
    """

    band: str
    evidence: list[RetrievedChunk]
