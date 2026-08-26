"""
LLM client interface and the Anthropic adapter used behind it.
"""

import base64
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

    @abstractmethod
    async def transcribe_document(
        self, data: bytes, media_type: str, prompt: str, schema: type[SchemaT]
    ) -> SchemaT:
        """Return a structured response to a prompt paired with an image or PDF attachment."""
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

    async def transcribe_document(
        self, data: bytes, media_type: str, prompt: str, schema: type[SchemaT]
    ) -> SchemaT:
        # Images and PDFs are different content block types in the Messages
        # API; everything else about the call is identical, so the only
        # branch needed is which block type wraps the same base64 source.
        # Structured output uses the same forced-tool-call trick as
        # generate_structured, just with an attachment block alongside the
        # prompt -- this is what lets the caller ask the model to judge the
        # attachment (e.g. "is this actually an assignment?") instead of
        # unconditionally producing text for whatever was uploaded.
        block_type = "image" if media_type.startswith("image/") else "document"
        attachment_block = {
            "type": block_type,
            "source": {
                "type": "base64",
                "media_type": media_type,
                "data": base64.standard_b64encode(data).decode(),
            },
        }
        tool_name = schema.__name__
        response = await self._client.messages.create(
            model=self._model,
            max_tokens=2048,
            messages=[
                {
                    "role": "user",
                    "content": [attachment_block, {"type": "text", "text": prompt}],
                }
            ],
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
