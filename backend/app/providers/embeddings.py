"""
Embedding client interface and the OpenAI adapter used behind it.
"""

from abc import ABC, abstractmethod

from openai import AsyncOpenAI


class EmbeddingClient(ABC):
    """
    Provider-agnostic interface for turning text into vectors, used at
    both ingestion time (chunk embedding) and query time. Kept separate
    from LLMClient because swapping this provider requires re-embedding
    the corpus, unlike swapping the generation provider.
    """

    @abstractmethod
    async def embed(self, texts: list[str]) -> list[list[float]]:
        """Return one embedding vector per input string, same order."""
        ...


class OpenAIEmbeddingClient(EmbeddingClient):
    """Concrete EmbeddingClient adapter backed by OpenAI's embeddings API."""

    def __init__(self, api_key: str, model: str = "text-embedding-3-small") -> None:
        self._client = AsyncOpenAI(api_key=api_key)
        self._model = model

    async def embed(self, texts: list[str]) -> list[list[float]]:
        response = await self._client.embeddings.create(model=self._model, input=texts)
        return [item.embedding for item in response.data]
