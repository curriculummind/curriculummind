"""
LLM client interface and the Anthropic adapter used behind it.
"""

from abc import ABC, abstractmethod
from collections.abc import AsyncIterator
from typing import TypeVar

from anthropic import AsyncAnthropic
from pydantic import BaseModel

SchemaT = TypeVar("SchemaT", bound=BaseModel)


class Message(BaseModel):
    """A single turn in a conversation passed to an LLM call."""

    role: str
    content: str


class LLMClient(ABC):
    """
    Provider-agnostic interface for the two ways the tutoring pipeline
    calls a language model: a structured classification call and a
    streamed generation call. Every pipeline node depends on this
    interface, never on a vendor SDK directly.
    """

    @abstractmethod
    async def generate_structured(
        self, messages: list[Message], schema: type[SchemaT], *, system: str | None = None
    ) -> SchemaT:
        """Return a single response validated against a Pydantic schema."""
        ...

    @abstractmethod
    async def generate_text(
        self, messages: list[Message], *, system: str | None = None
    ) -> AsyncIterator[str]:
        """Yield response text incrementally for streaming to the client."""
        ...


class AnthropicLLMClient(LLMClient):
    """Concrete LLMClient adapter backed by the Anthropic Messages API."""

    def __init__(self, api_key: str, model: str = "claude-sonnet-4-5") -> None:
        self._client = AsyncAnthropic(api_key=api_key)
        self._model = model

    async def generate_structured(
        self, messages: list[Message], schema: type[SchemaT], *, system: str | None = None
    ) -> SchemaT:
        # Structured output is implemented as a single forced tool call: the
        # target Pydantic schema becomes the tool's input schema, so Claude's
        # response is guaranteed to match it rather than being parsed out of
        # free text.
        tool_name = schema.__name__
        response = await self._client.messages.create(
            model=self._model,
            max_tokens=1024,
            system=system or "",
            messages=[{"role": m.role, "content": m.content} for m in messages],
            tools=[
                {
                    "name": tool_name,
                    "description": schema.__doc__ or f"Return a {tool_name}.",
                    "input_schema": schema.model_json_schema(),
                }
            ],
            tool_choice={"type": "tool", "name": tool_name},
        )
        tool_use = next(block for block in response.content if block.type == "tool_use")
        return schema.model_validate(tool_use.input)

    async def generate_text(
        self, messages: list[Message], *, system: str | None = None
    ) -> AsyncIterator[str]:
        async with self._client.messages.stream(
            model=self._model,
            max_tokens=2048,
            system=system or "",
            messages=[{"role": m.role, "content": m.content} for m in messages],
        ) as stream:
            async for text in stream.text_stream:
                yield text
