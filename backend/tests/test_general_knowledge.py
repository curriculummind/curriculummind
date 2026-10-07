"""Unit tests for general-knowledge answerability classification (Decisions 033, 035)."""

from collections.abc import AsyncIterator

from app.providers.llm import LLMClient, Message
from app.tutoring.general_knowledge import (
    classify_answerable_generally,
    classify_topic_in_scope,
)


class FakeLLMClient(LLMClient):
    """Stub LLMClient returning a fixed answerability verdict, for testing without a real API call."""

    def __init__(self, can_answer: bool) -> None:
        self._can_answer = can_answer

    async def generate_structured(self, messages, schema, *, system=None):
        return schema(can_answer=self._can_answer)

    async def generate_text(self, messages: list[Message], *, system: str | None = None) -> AsyncIterator[str]:
        raise NotImplementedError

    async def transcribe_document(self, data: bytes, media_type: str, prompt: str, schema):
        raise NotImplementedError


class FakeTopicScopeLLMClient(LLMClient):
    """Stub LLMClient returning a fixed in-scope verdict, for testing without a real API call."""

    def __init__(self, in_scope: bool) -> None:
        self._in_scope = in_scope

    async def generate_structured(self, messages, schema, *, system=None):
        return schema(in_scope=self._in_scope)

    async def generate_text(self, messages: list[Message], *, system: str | None = None) -> AsyncIterator[str]:
        raise NotImplementedError

    async def transcribe_document(self, data: bytes, media_type: str, prompt: str, schema):
        raise NotImplementedError


async def test_classify_answerable_generally_returns_true_for_a_real_concept() -> None:
    """A legitimate, in-subject prerequisite concept classifies as answerable."""
    llm = FakeLLMClient(can_answer=True)
    result = await classify_answerable_generally("what is a decimal", "math", "6", llm)
    assert result is True


async def test_classify_answerable_generally_returns_false_for_off_subject_questions() -> None:
    """A question unrelated to the subject classifies as not answerable this way."""
    llm = FakeLLMClient(can_answer=False)
    result = await classify_answerable_generally("who won the super bowl", "math", "6", llm)
    assert result is False


async def test_classify_topic_in_scope_returns_true_for_a_covered_topic() -> None:
    """A question that goes deeper on a topic this course covers classifies as in scope."""
    llm = FakeTopicScopeLLMClient(in_scope=True)
    result = await classify_topic_in_scope(
        "why do we need decimals when we have ratios", ["Ratios and Unit Rates", "Decimal Operations"], "math", "6", llm
    )
    assert result is True


async def test_classify_topic_in_scope_returns_false_for_a_topic_not_in_this_course() -> None:
    """A real but out-of-course concept classifies as not in scope, falling through to the prerequisite check."""
    llm = FakeTopicScopeLLMClient(in_scope=False)
    result = await classify_topic_in_scope(
        "what is the Pythagorean theorem", ["Ratios and Unit Rates", "Decimal Operations"], "math", "6", llm
    )
    assert result is False
