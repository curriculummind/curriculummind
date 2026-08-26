"""
Worksheet photo/PDF/Word transcription.

Lets a student attach a photo, PDF, or Word document of an assignment
instead of typing it out. The file is never persisted -- it is held in
memory only long enough to extract its text, and only the resulting
plain text (identical in shape to a typed question) is returned to the
client for the student to review and edit before it enters the tutoring
pipeline. Retrieval, confidence gating, and assignment detection all
then run on that text exactly as they do for a typed question -- this
module adds a new input path, not a new pipeline.

Word documents are already digital text, so they're extracted
mechanically (python-docx) rather than sent through the vision LLM call
images and PDFs need -- cheaper, faster, and no OCR risk.

The vision path judges relevance before transcribing (transcribe_upload
returns None when it doesn't) -- an early version transcribed whatever
was in the image unconditionally, so an unrelated photo (a construction
site plan, a random object) still produced text that silently populated
the question box. That's a different failure than a curriculum-content
gap: it isn't about subject matching -- the existing retrieval
confidence gate already handles "this is a real question but I have no
material for it" once valid text reaches /tutor/ask. This is about
rejecting inputs that were never assignment content at all, before they
reach the pipeline.
"""

import io

from docx import Document
from pydantic import BaseModel

from app.providers.llm import LLMClient

DOCX_MEDIA_TYPE = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"

TRANSCRIBE_PROMPT = (
    "Look at the attached image or document. First decide: does it show a "
    "specific academic assignment, worksheet, or homework problem -- actual "
    "problem text meant to be solved or answered? This does NOT include an "
    "unrelated photo, diagram, map, site plan, or object with no problem to "
    "solve.\n\n"
    "If it does, set is_assignment_content to true and transcribe the "
    "problem text into `text` exactly as written -- preserve numbering, "
    "exact numbers, and wording. Do not solve it, explain it, or add "
    "anything not present in the source. If it contains multiple problems, "
    "transcribe all of them.\n\n"
    "If it does not show an assignment or worksheet problem, set "
    "is_assignment_content to false and leave `text` empty."
)


class AttachmentTranscription(BaseModel):
    """Whether an attachment shows assignment/worksheet content, and its transcription if so."""

    is_assignment_content: bool
    text: str


def _extract_docx_text(data: bytes) -> str:
    """Mechanically extract paragraph text from a .docx file."""
    document = Document(io.BytesIO(data))
    return "\n".join(paragraph.text for paragraph in document.paragraphs if paragraph.text.strip())


async def transcribe_upload(data: bytes, media_type: str, llm: LLMClient) -> str | None:
    """Return the transcribed assignment text, or None if the upload isn't assignment/worksheet content."""
    if media_type == DOCX_MEDIA_TYPE:
        return _extract_docx_text(data)
    result = await llm.transcribe_document(data, media_type, TRANSCRIBE_PROMPT, AttachmentTranscription)
    return result.text if result.is_assignment_content else None
