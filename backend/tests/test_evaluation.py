"""Unit tests for the RAGAS-style evaluation metrics (Decision 032)."""

from collections.abc import AsyncIterator, Callable

from pydantic import BaseModel

from app.providers.embeddings import EmbeddingClient
from app.providers.llm import LLMClient, Message
from app.rag_eval.answer_relevancy import (
    GeneratedQuestions,
    _cosine_similarity,
    score_answer_relevancy,
)
from app.rag_eval.context_precision import judge_relevance, score_context_precision
from app.rag_eval.context_recall import FactCoverage, score_context_recall
from app.rag_eval.faithfulness import ClaimJudgment, Claims, score_faithfulness
from app.retrieval.models import RetrievedChunk
from app.retrieval.relevance import RelevanceJudgment


class FakeLLMClient(LLMClient):
    """Stub LLMClient delegating structured responses to a test-supplied callable, for varied canned responses."""

    def __init__(self, responder: Callable[[list[Message], type], BaseModel]) -> None:
        self._responder = responder

    async def generate_structured(self, messages: list[Message], schema, *, system: str | None = None):
        return self._responder(messages, schema)

    async def generate_text(self, messages: list[Message], *, system: str | None = None) -> AsyncIterator[str]:
        raise NotImplementedError

    async def transcribe_document(self, data: bytes, media_type: str, prompt: str, schema):
        raise NotImplementedError


class FakeEmbeddingClient(EmbeddingClient):
    """Stub EmbeddingClient returning a fixed vector per input string, looked up by exact text."""

    def __init__(self, vectors: dict[str, list[float]]) -> None:
        self._vectors = vectors

    async def embed(self, texts: list[str]) -> list[list[float]]:
        return [self._vectors[text] for text in texts]


def _refuses_to_be_called(*_args, **_kwargs):
    raise AssertionError("LLM/embedder should not have been called")


def _chunk(content: str) -> RetrievedChunk:
    return RetrievedChunk(
        chunk_id="c1",
        resource_id="r1",
        resource_title="Test Resource",
        source_url="https://example.com",
        license="test",
        content=content,
        similarity=0.5,
    )


async def test_context_precision_scores_fraction_of_relevant_chunks() -> None:
    """Two of three chunks judged relevant yields a precision of 2/3."""
    evidence = [_chunk("about ratios"), _chunk("about cells"), _chunk("ratios again")]
    llm = FakeLLMClient(lambda messages, schema: RelevanceJudgment(can_answer="ratios" in messages[0].content))
    score = await score_context_precision("what is a ratio", evidence, llm)
    assert score == 2 / 3


async def test_context_precision_returns_zero_for_empty_evidence() -> None:
    """No retrieved chunks means zero precision, without calling the LLM at all."""
    llm = FakeLLMClient(_refuses_to_be_called)
    assert await score_context_precision("anything", [], llm) == 0.0


async def test_judge_relevance_preserves_evidence_order() -> None:
    """judge_relevance returns one judgment per chunk, in the same order the chunks were given."""
    evidence = [_chunk("about ratios"), _chunk("about cells"), _chunk("ratios again")]
    llm = FakeLLMClient(lambda messages, schema: RelevanceJudgment(can_answer="ratios" in messages[0].content))
    assert await judge_relevance("what is a ratio", evidence, llm) == [True, False, True]


async def test_judge_relevance_returns_empty_list_for_empty_evidence() -> None:
    """No retrieved chunks means no judgments, without calling the LLM at all."""
    llm = FakeLLMClient(_refuses_to_be_called)
    assert await judge_relevance("anything", [], llm) == []


async def test_context_recall_scores_fraction_of_facts_present() -> None:
    """One of two reference facts marked present yields a recall of 0.5."""
    llm = FakeLLMClient(lambda messages, schema: FactCoverage(present=[True, False]))
    score = await score_context_recall(["fact a", "fact b"], [_chunk("evidence")], llm)
    assert score == 0.5


async def test_context_recall_returns_zero_for_empty_evidence() -> None:
    """No retrieved evidence means zero recall, without calling the LLM at all."""
    llm = FakeLLMClient(_refuses_to_be_called)
    assert await score_context_recall(["fact a"], [], llm) == 0.0


async def test_context_recall_falls_back_gracefully_on_length_mismatch() -> None:
    """A malformed judgment with the wrong number of entries still produces a score, not a crash."""
    llm = FakeLLMClient(lambda messages, schema: FactCoverage(present=[True]))
    score = await score_context_recall(["fact a", "fact b", "fact c"], [_chunk("evidence")], llm)
    assert score == 1.0


async def test_faithfulness_scores_fraction_of_supported_claims() -> None:
    """One of two claims supported by the evidence yields a faithfulness of 0.5."""
    llm = FakeLLMClient(
        lambda messages, schema: Claims(
            claims=[
                ClaimJudgment(text="supported claim", supported=True),
                ClaimJudgment(text="unsupported claim", supported=False),
            ]
        )
    )
    score = await score_faithfulness("some answer", [_chunk("evidence")], llm)
    assert score == 0.5


async def test_faithfulness_returns_one_when_answer_makes_no_claims() -> None:
    """An answer with no checkable claims (e.g. a pure question) is trivially faithful."""
    llm = FakeLLMClient(lambda messages, schema: Claims(claims=[]))
    score = await score_faithfulness("what do you think?", [_chunk("evidence")], llm)
    assert score == 1.0


async def test_answer_relevancy_averages_cosine_similarity_to_generated_questions() -> None:
    """Mean cosine similarity between the original question and three reverse-engineered questions."""
    llm = FakeLLMClient(lambda messages, schema: GeneratedQuestions(questions=["q1", "q2", "q3"]))
    embedder = FakeEmbeddingClient(
        {
            "what is a ratio": [1.0, 0.0, 0.0],
            "q1": [1.0, 0.0, 0.0],
            "q2": [0.0, 1.0, 0.0],
            "q3": [1.0, 0.0, 0.0],
        }
    )
    score = await score_answer_relevancy("what is a ratio", "some answer", llm, embedder)
    assert score == (1.0 + 0.0 + 1.0) / 3


async def test_answer_relevancy_returns_zero_when_no_questions_generated() -> None:
    """No reverse-engineered questions means zero relevancy, without calling the embedder at all."""
    llm = FakeLLMClient(lambda messages, schema: GeneratedQuestions(questions=[]))
    embedder = FakeEmbeddingClient({})
    score = await score_answer_relevancy("what is a ratio", "some answer", llm, embedder)
    assert score == 0.0


def test_cosine_similarity_of_identical_vectors_is_one() -> None:
    """Two identical vectors have a cosine similarity of exactly 1."""
    assert _cosine_similarity([1.0, 2.0, 3.0], [1.0, 2.0, 3.0]) == 1.0


def test_cosine_similarity_of_orthogonal_vectors_is_zero() -> None:
    """Two orthogonal vectors have a cosine similarity of exactly 0."""
    assert _cosine_similarity([1.0, 0.0], [0.0, 1.0]) == 0.0


def test_cosine_similarity_guards_against_zero_vector() -> None:
    """A zero vector (e.g. a degenerate embedding) returns 0 rather than dividing by zero."""
    assert _cosine_similarity([0.0, 0.0], [1.0, 1.0]) == 0.0
