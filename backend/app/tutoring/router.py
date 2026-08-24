"""
HTTP route for the M0 ask-a-question flow.

No conversation persistence yet -- a single question in, a single
streamed grounded response out. Persisting conversations/messages and
the full pedagogical pipeline (safety, assignment detection, strategy
selection) are M1 work.
"""

from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from app.config import get_settings
from app.db import get_pool
from app.identity.auth import get_current_user_id
from app.providers.embeddings import OpenAIEmbeddingClient
from app.providers.llm import AnthropicLLMClient
from app.retrieval.pipeline import retrieve
from app.tutoring.generation import generate_grounded_response

router = APIRouter(prefix="/tutor", tags=["tutoring"])


class AskRequest(BaseModel):
    """A single tutoring question, scoped to one subject and grade band."""

    question: str
    subject: str
    grade_band: str = "6"


NO_EVIDENCE_MESSAGE = (
    "I don't have curriculum material covering that yet. Try asking about "
    "ratios, unit rates, expressions, equations, ecosystems, or cells."
)


@router.post("/ask")
async def ask(request: AskRequest, user_id: str = Depends(get_current_user_id)) -> StreamingResponse:
    """Retrieve grounding evidence and stream a generated response."""
    settings = get_settings()
    embedder = OpenAIEmbeddingClient(api_key=settings.openai_api_key, model=settings.openai_embedding_model)
    llm = AnthropicLLMClient(api_key=settings.anthropic_api_key, model=settings.anthropic_model)

    result = await retrieve(
        request.question,
        subject_slug=request.subject,
        grade_band=request.grade_band,
        embedder=embedder,
        pool=get_pool(),
    )

    if result.band == "low":

        async def fallback():
            yield NO_EVIDENCE_MESSAGE

        return StreamingResponse(fallback(), media_type="text/plain")

    stream = generate_grounded_response(
        request.question,
        result.evidence[:3],
        subject=request.subject,
        grade_band=request.grade_band,
        llm=llm,
    )
    return StreamingResponse(stream, media_type="text/plain")
