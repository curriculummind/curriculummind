"""Unit tests for the content-safety guardrail."""

from collections.abc import AsyncIterator

from app.providers.llm import LLMClient, Message
from app.tutoring.safety import CRISIS_MESSAGE, DECLINE_MESSAGE, classify_safety, response_for, should_block


class FakeLLMClient(LLMClient):
    """Stub LLMClient returning a fixed safety category, for testing without a real API call."""

    def __init__(self, category: str) -> None:
        self._category = category

    async def generate_structured(self, messages, schema, *, system=None):
        return schema(category=self._category)

    async def generate_text(self, messages: list[Message], *, system: str | None = None) -> AsyncIterator[str]:
        raise NotImplementedError

    async def transcribe_document(self, data: bytes, media_type: str, prompt: str, schema):
        raise NotImplementedError


async def test_classify_safety_returns_the_classified_category() -> None:
    """classify_safety passes through whatever category the model returns."""
    llm = FakeLLMClient(category="sensitive_topic")
    result = await classify_safety("how do people reproduce", llm)
    assert result == "sensitive_topic"


async def test_classify_safety_returns_none_for_ordinary_questions() -> None:
    """An ordinary curriculum question classifies as 'none'."""
    llm = FakeLLMClient(category="none")
    result = await classify_safety("what is a ratio", llm)
    assert result == "none"


def test_prompt_injection_unsafe_content_and_crisis_block() -> None:
    """The three categories that need a short-circuited response should all block tutoring."""
    assert should_block("prompt_injection") is True
    assert should_block("unsafe_content") is True
    assert should_block("crisis") is True


def test_sensitive_topic_and_pii_do_not_block() -> None:
    """A legitimate-but-sensitive question or shared PII should still be tutored, just flagged."""
    assert should_block("sensitive_topic") is False
    assert should_block("pii") is False


def test_none_does_not_block() -> None:
    """An ordinary question never blocks."""
    assert should_block("none") is False


def test_crisis_gets_the_compassionate_message_not_the_generic_decline() -> None:
    """A self-harm disclosure must not get the same flat refusal as a bomb-making request."""
    assert response_for("crisis") == CRISIS_MESSAGE
    assert "988" in response_for("crisis")


def test_unsafe_content_and_prompt_injection_get_the_generic_decline() -> None:
    """Categories other than crisis use the plain decline message."""
    assert response_for("unsafe_content") == DECLINE_MESSAGE
    assert response_for("prompt_injection") == DECLINE_MESSAGE
