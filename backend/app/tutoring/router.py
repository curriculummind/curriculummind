"""
HTTP route for the tutoring ask flow, with conversation persistence.

Conversation history is now loaded and included in the generation call,
and both turns are persisted. The decision phase -- the content-safety
guardrail (Decision 022), retrieval, assignment detection (Decision
017), the low-confidence relevance fallback (Decision 016), and
struggle-escalation strategy selection (Decision 019) -- runs as a
single LangGraph invocation (Decision 006, `app/tutoring/graph.py`);
this route is left with conversation lifecycle, running that graph,
and streaming/persisting the generated response.
"""

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from app.config import get_settings
from app.db import get_pool
from app.identity.auth import get_current_user_id
from app.identity.profiles import get_profile
from app.providers.embeddings import OpenAIEmbeddingClient
from app.providers.llm import AnthropicLLMClient, Message
from app.tutoring.attachments import transcribe_upload
from app.tutoring.conversations import (
    append_message,
    create_conversation,
    get_conversation_owner,
    get_messages,
    get_tutoring_state,
    record_flagged_interaction,
    update_tutoring_state,
)
from app.tutoring.generation import generate_grounded_response
from app.tutoring.graph import run_tutoring_pipeline
from app.tutoring.safety import SENSITIVE_NO_EVIDENCE_MESSAGE, response_for
from app.observability.traces import record_decision_trace

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
    tutoring_state = await get_tutoring_state(pool, conversation_id)
    decision = await run_tutoring_pipeline(
        question=request.question,
        retrieval_query=retrieval_query,
        subject=request.subject,
        grade_band=request.grade_band,
        history=history,
        llm=llm,
        embedder=embedder,
        tutoring_phase=tutoring_state["tutoring_phase"],
        struggle_count=tutoring_state["struggle_count"],
        confirm_count=tutoring_state["confirm_count"],
    )

    safety_category = decision.get("safety_category", "none")
    if safety_category != "none":
        await record_flagged_interaction(
            pool,
            conversation_id,
            user_id,
            category=safety_category,
            question=request.question,
            blocked=decision.get("safety_blocked", False),
        )

    async def stream_and_persist(text_stream):
        pieces: list[str] = []
        async for token in text_stream:
            pieces.append(token)
            yield token
        await append_message(pool, conversation_id, "assistant", "".join(pieces))

    trace_evidence_chunk_ids: list[str] = []
    trace_strategy: str | None = None
    trace_correctness: str | None = None
    struggle_count_after = tutoring_state["struggle_count"]
    confirm_count_after = tutoring_state["confirm_count"]

    if decision.get("safety_blocked"):
        response_phase = tutoring_state["tutoring_phase"]
        trace_is_assignment = None

        async def declined():
            yield response_for(safety_category)

        body = stream_and_persist(declined())
    elif decision["band"] == "low":
        response_phase = tutoring_state["tutoring_phase"]
        trace_is_assignment = decision.get("is_assignment")
        trace_correctness = decision.get("correctness")
        message = SENSITIVE_NO_EVIDENCE_MESSAGE if safety_category == "sensitive_topic" else NO_EVIDENCE_MESSAGE

        async def fallback():
            yield message

        body = stream_and_persist(fallback())
    else:
        response_phase = decision["new_phase"]
        trace_is_assignment = decision["is_assignment"]
        trace_strategy = decision["strategy"]
        trace_correctness = decision.get("correctness")
        trace_evidence_chunk_ids = [chunk.chunk_id for chunk in decision["evidence"][:3]]
        struggle_count_after = decision["new_struggle_count"]
        confirm_count_after = decision["new_confirm_count"]
        await update_tutoring_state(
            pool,
            conversation_id,
            tutoring_phase=decision["new_phase"],
            struggle_count=decision["new_struggle_count"],
            confirm_count=decision["new_confirm_count"],
        )

        body = stream_and_persist(
            generate_grounded_response(
                request.question,
                decision["evidence"][:3],
                history,
                subject=request.subject,
                grade_band=request.grade_band,
                llm=llm,
                is_assignment=decision["is_assignment"],
                strategy=decision["strategy"],
            )
        )

    await record_decision_trace(
        pool,
        conversation_id,
        user_id,
        question=request.question,
        safety_category=safety_category,
        band=decision.get("band"),
        strategy=trace_strategy,
        is_assignment=trace_is_assignment,
        evidence_chunk_ids=trace_evidence_chunk_ids,
        correctness=trace_correctness,
        tutoring_phase_before=tutoring_state["tutoring_phase"],
        tutoring_phase_after=response_phase,
        struggle_count_before=tutoring_state["struggle_count"],
        struggle_count_after=struggle_count_after,
        confirm_count_before=tutoring_state["confirm_count"],
        confirm_count_after=confirm_count_after,
    )

    response = StreamingResponse(body, media_type="text/plain")
    response.headers["X-Conversation-Id"] = conversation_id
    response.headers["X-Tutoring-Phase"] = response_phase
    return response


@router.post("/transcribe")
async def transcribe(
    file: UploadFile = File(...), user_id: str = Depends(get_current_user_id)
) -> dict[str, str]:
    """Transcribe an uploaded worksheet photo or PDF to plain text, without persisting the file."""
    settings = get_settings()

    if file.content_type not in settings.allowed_upload_mime_types:
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail="Unsupported file type. Please attach a JPEG, PNG, WEBP, PDF, or Word (.docx) file.",
        )

    data = await file.read()
    if len(data) > settings.max_upload_bytes:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail="File is too large.",
        )

    llm = AnthropicLLMClient(api_key=settings.anthropic_api_key, model=settings.anthropic_model)
    text = await transcribe_upload(data, file.content_type, llm)
    if text is None:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=(
                "That doesn't look like an assignment or worksheet problem. "
                "Try attaching a photo of your homework question instead."
            ),
        )
    return {"text": text}
