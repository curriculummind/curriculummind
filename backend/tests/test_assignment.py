"""Unit tests for assignment-like request detection."""

from collections.abc import AsyncIterator

from app.providers.llm import LLMClient, Message
from app.tutoring.assignment import AssignmentClassification, detect_assignment


class FakeLLMClient(LLMClient):
    """Stub LLMClient returning a fixed classification, for testing without a real API call."""

    def __init__(self, is_assignment: bool) -> None:
        self._is_assignment = is_assignment

    async def generate_structured(self, messages, schema, *, system=None):
        return schema(is_assignment=self._is_assignment)

    async def generate_text(self, messages: list[Message], *, system: str | None = None) -> AsyncIterator[str]:
        raise NotImplementedError

    async def transcribe_document(self, data: bytes, media_type: str, prompt: str, schema):
        raise NotImplementedError


async def test_detect_assignment_true_passes_through_classification() -> None:
    """When the model classifies the question as an assignment, detect_assignment returns True."""
    llm = FakeLLMClient(is_assignment=True)
    assert await detect_assignment("Solve for x: 3x - 7 = 20", llm) is True


async def test_detect_assignment_false_passes_through_classification() -> None:
    """When the model classifies the question as conceptual, detect_assignment returns False."""
    llm = FakeLLMClient(is_assignment=False)
    assert await detect_assignment("What is a ratio?", llm) is False


def test_assignment_classification_schema_has_expected_field() -> None:
    """The schema exposes a single boolean field used by the pipeline."""
    classification = AssignmentClassification(is_assignment=True)
    assert classification.is_assignment is True
