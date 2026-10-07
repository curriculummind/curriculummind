"""
Public waitlist signup (Decision 034).

The only unauthenticated, write-accepting endpoint in the backend --
everything else requires a Supabase Auth session (Decision 010). That's
deliberate here: this exists to capture interest from a parent or
teacher before they're ready to create a full account, so it can't
require one. Writes still go through the backend's own connection, the
same posture as every other write in this app -- `waitlist_signups` has
RLS enabled with no policies, since nothing ever reads or writes it
through a client-side Supabase call.
"""

from typing import Literal

from fastapi import APIRouter, status
from pydantic import BaseModel

from app.db import get_pool

router = APIRouter(prefix="/waitlist", tags=["waitlist"])


class WaitlistSignup(BaseModel):
    """An expression of interest from someone not yet ready to create an account."""

    email: str
    interest: Literal["parent", "teacher"]


@router.post("", status_code=status.HTTP_201_CREATED)
async def join_waitlist(data: WaitlistSignup) -> dict[str, str]:
    """Record interest, idempotently -- resubmitting the same email is a no-op, not an error."""
    pool = get_pool()
    async with pool.connection() as conn:
        await conn.execute(
            "insert into waitlist_signups (email, interest) values (%s, %s) on conflict (email) do nothing",
            (data.email.strip().lower(), data.interest),
        )
    return {"status": "ok"}
