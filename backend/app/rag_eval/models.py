"""Data shapes produced by the RAGAS-style evaluation harness."""

from pydantic import BaseModel


class CaseResult(BaseModel):
    """
    The outcome of running one golden-set case through the real
    retrieval + generation pipeline and scoring it.

    The four RAGAS-style scores are None for a fallback case (nothing
    was retrieved to score faithfulness/precision/recall/relevancy
    against) -- `fallback_correct` is the only field that applies there.
    """

    case_id: str
    question: str
    band: str
    evidence_count: int
    answer: str | None = None
    context_precision: float | None = None
    context_recall: float | None = None
    faithfulness: float | None = None
    answer_relevancy: float | None = None
    expect_fallback: bool = False
    fallback_correct: bool | None = None
    notes: str = ""
