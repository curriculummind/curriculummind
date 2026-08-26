"""Unit tests for answer correctness classification."""

from collections.abc import AsyncIterator

from app.providers.llm import LLMClient, Message
from app.tutoring.correctness import classify_answer


class FakeLLMClient(LLMClient):
    """Stub LLMClient returning a fixed classification status, for testing without a real API call."""

    def __init__(self, status: str) -> None:
        self._status = status

    async def generate_structured(self, messages, schema, *, system=None):
        return schema(status=self._status)

    async def generate_text(self, messages: list[Message], *, system: str | None = None) -> AsyncIterator[str]:
        raise NotImplementedError

    async def transcribe_document(self, data: bytes, media_type: str, prompt: str, schema):
        raise NotImplementedError


async def test_classify_answer_returns_correct() -> None:
    """When the model classifies the answer as correct, classify_answer returns 'correct'."""
    llm = FakeLLMClient(status="correct")
    result = await classify_answer("What is 2 + 2?", "4", llm)
    assert result == "correct"


async def test_classify_answer_returns_incorrect() -> None:
    """When the model classifies the answer as incorrect, classify_answer returns 'incorrect'."""
    llm = FakeLLMClient(status="incorrect")
    result = await classify_answer("What is 2 + 2?", "5", llm)
    assert result == "incorrect"


async def test_classify_answer_returns_unclear() -> None:
    """When the model classifies the answer as unclear, classify_answer returns 'unclear'."""
    llm = FakeLLMClient(status="unclear")
    result = await classify_answer("What is 2 + 2?", "I don't know", llm)
    assert result == "unclear"
