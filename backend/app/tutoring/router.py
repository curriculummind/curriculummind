"""
HTTP route for the tutoring ask flow, with conversation persistence.

Conversation history is now loaded and included in the generation call,
and both turns are persisted -- the pedagogical pipeline (safety,
assignment detection, strategy selection beyond the single guided-
discovery default) is still M1 work.
"""

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from app.config import get_settings
from app.db import get_pool
from app.identity.auth import get_current_user_id
from app.identity.profiles import get_profile
from app.providers.embeddings import OpenAIEmbeddingClient
from app.providers.llm import AnthropicLLMClient, Message
from app.retrieval.pipeline import retrieve
from app.tutoring.conversations import (
    append_message,
    create_conversation,
    get_conversation_owner,
    get_messages,
)
from app.tutoring.generation import generate_grounded_response

router = APIRouter(prefix="/tutor", tags=["tutoring"])

DB_ROLE_TO_LLM_ROLE = {"student": "user", "assistant": "assistant"}

NO_EVIDENCE_MESSAGE = (
    "I don't have curriculum material covering that yet. Try asking about "
    "ratios, unit rates, expressions, equations, ecosystems, or cells."
)


def _build_retrieval_query(question: str, history: list[Message]) -> str:
    """
    Combine recent conversation turns with the new question for retrieval.

    A short follow-up like "is that right?" or "1:2 i think" has no topic
    keywords of its own -- embedding it alone fails the confidence gate
    even when the topic is obvious from context. This is a cheap
    concatenation, not real query rewriting (architecture §15 flags that
    as a future improvement); it's enough to keep a guided-discovery
    follow-up from silently losing its grounding.
    """
    if not history:
        return question
    recent_context = " ".join(message.content for message in history[-2:])
    return f"{recent_context} {question}"


class AskRequest(BaseModel):
    """A tutoring question, optionally continuing an existing conversation."""

    question: str
    subject: str
    grade_band: str = "6"
    conversation_id: str | None = None


@router.post("/ask")
async def ask(request: AskRequest, user_id: str = Depends(get_current_user_id)) -> StreamingResponse:
    """Load conversation history, retrieve evidence, and stream a response, persisting both turns."""
    pool = get_pool()
    settings = get_settings()

    if await get_profile(pool, user_id) is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Profile not set up yet. Complete sign-up before asking a question.",
        )

    if request.conversation_id is None:
        conversation_id = await create_conversation(pool, user_id, request.subject)
    else:
        owner_id = await get_conversation_owner(pool, request.conversation_id)
        if owner_id is None or owner_id != user_id:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="conversation not found")
        conversation_id = request.conversation_id

    history_rows = await get_messages(pool, conversation_id)
    history = [
        Message(role=DB_ROLE_TO_LLM_ROLE[row["role"]], content=row["content"]) for row in history_rows
    ]

    await append_message(pool, conversation_id, "student", request.question)

    embedder = OpenAIEmbeddingClient(api_key=settings.openai_api_key, model=settings.openai_embedding_model)
    llm = AnthropicLLMClient(api_key=settings.anthropic_api_key, model=settings.anthropic_model)

    retrieval_query = _build_retrieval_query(request.question, history)
    result = await retrieve(
        retrieval_query,
        subject_slug=request.subject,
        grade_band=request.grade_band,
        embedder=embedder,
        pool=pool,
    )

    async def stream_and_persist(text_stream):
        pieces: list[str] = []
        async for token in text_stream:
            pieces.append(token)
            yield token
        await append_message(pool, conversation_id, "assistant", "".join(pieces))

    if result.band == "low":

        async def fallback():
            yield NO_EVIDENCE_MESSAGE

        body = stream_and_persist(fallback())
    else:
        body = stream_and_persist(
            generate_grounded_response(
                request.question,
                result.evidence[:3],
                history,
                subject=request.subject,
                grade_band=request.grade_band,
                llm=llm,
            )
        )

    response = StreamingResponse(body, media_type="text/plain")
    response.headers["X-Conversation-Id"] = conversation_id
    return response
