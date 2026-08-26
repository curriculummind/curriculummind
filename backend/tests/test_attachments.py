"""Unit tests for attachment transcription and its non-assignment rejection path."""

from collections.abc import AsyncIterator

from app.providers.llm import LLMClient, Message
from app.tutoring.attachments import AttachmentTranscription, transcribe_upload


class FakeLLMClient(LLMClient):
    """Stub LLMClient returning a fixed transcription result, for testing without a real API call."""

    def __init__(self, is_assignment_content: bool, text: str = "") -> None:
        self._is_assignment_content = is_assignment_content
        self._text = text

    async def generate_structured(self, messages, schema, *, system=None):
        raise NotImplementedError

    async def generate_text(self, messages: list[Message], *, system: str | None = None) -> AsyncIterator[str]:
        raise NotImplementedError

    async def transcribe_document(self, data: bytes, media_type: str, prompt: str, schema):
        return schema(is_assignment_content=self._is_assignment_content, text=self._text)


async def test_transcribe_upload_returns_text_for_assignment_content() -> None:
    """When the model judges the attachment as assignment content, its transcription is returned."""
    llm = FakeLLMClient(is_assignment_content=True, text="Solve for x: 2x + 5 = 13")
    result = await transcribe_upload(b"fake-image-bytes", "image/png", llm)
    assert result == "Solve for x: 2x + 5 = 13"


async def test_transcribe_upload_returns_none_for_non_assignment_content() -> None:
    """When the model judges the attachment as unrelated to an assignment, transcribe_upload returns None."""
    llm = FakeLLMClient(is_assignment_content=False)
    result = await transcribe_upload(b"fake-image-bytes", "image/png", llm)
    assert result is None


def test_attachment_transcription_schema_has_expected_fields() -> None:
    """The schema exposes both the relevance flag and the transcribed text."""
    transcription = AttachmentTranscription(is_assignment_content=True, text="1) Find x.")
    assert transcription.is_assignment_content is True
    assert transcription.text == "1) Find x."
