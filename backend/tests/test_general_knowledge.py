"""Unit tests for general-knowledge answerability classification (Decision 033)."""

from collections.abc import AsyncIterator

from app.providers.llm import LLMClient, Message
from app.tutoring.general_knowledge import classify_answerable_generally


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
