"""Unit tests for answer correctness classification."""

from collections.abc import AsyncIterator

from app.providers.llm import LLMClient, Message
from app.tutoring.correctness import _last_question, classify_answer


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


def test_last_question_isolates_trailing_question_from_anchor() -> None:
    """A blank-line-separated anchor and question returns only the question."""
    message = (
        "For every 8 hamburgers, there are 6 hotdogs, that's your ratio, 6 to 8.\n\n"
        "24 is how many groups of 8?"
    )
    assert _last_question(message) == "24 is how many groups of 8?"


def test_last_question_falls_back_to_whole_message_without_blank_line() -> None:
    """A message with no blank-line-separated question returns unchanged, not truncated."""
    message = "Not quite, try again."
    assert _last_question(message) == message


def test_last_question_falls_back_when_last_segment_is_not_a_question() -> None:
    """A blank-line-separated closing statement that isn't a question returns the whole message."""
    message = "You're on the right track.\n\nKeep going with that approach."
    assert _last_question(message) == message
