"""
Conversation and message persistence.

Conversation memory (architecture §12): short-term, per-thread context,
distinct from the longer-term student learning context, which isn't
built yet. This is what lets a guided-discovery question actually get
followed up on -- without it, every /tutor/ask call was context-free.
"""

from psycopg.rows import dict_row
from psycopg_pool import AsyncConnectionPool


async def get_subject_id(pool: AsyncConnectionPool, slug: str) -> str:
    """Look up a subject's id by slug."""
    async with pool.connection() as conn:
        async with conn.cursor(row_factory=dict_row) as cur:
            await cur.execute("select id from subjects where slug = %s", (slug,))
            row = await cur.fetchone()
    if row is None:
        raise ValueError(f"unknown subject: {slug}")
    return str(row["id"])


async def create_conversation(pool: AsyncConnectionPool, student_id: str, subject_slug: str) -> str:
    """Start a new conversation for a student in a subject."""
    subject_id = await get_subject_id(pool, subject_slug)
    async with pool.connection() as conn:
        async with conn.cursor(row_factory=dict_row) as cur:
            await cur.execute(
                "insert into conversations (student_id, subject_id) values (%s, %s) returning id",
                (student_id, subject_id),
            )
            row = await cur.fetchone()
    return str(row["id"])


async def get_conversation_owner(pool: AsyncConnectionPool, conversation_id: str) -> str | None:
    """Return a conversation's student_id, or None if the conversation doesn't exist."""
    async with pool.connection() as conn:
        async with conn.cursor(row_factory=dict_row) as cur:
            await cur.execute("select student_id from conversations where id = %s", (conversation_id,))
            row = await cur.fetchone()
    return str(row["student_id"]) if row else None


async def get_tutoring_state(pool: AsyncConnectionPool, conversation_id: str) -> dict:
    """Return a conversation's struggle-escalation state: phase and both counters."""
    async with pool.connection() as conn:
        async with conn.cursor(row_factory=dict_row) as cur:
            await cur.execute(
                "select tutoring_phase, struggle_count, confirm_count from conversations where id = %s",
                (conversation_id,),
            )
            row = await cur.fetchone()
    return dict(row)


async def update_tutoring_state(
    pool: AsyncConnectionPool,
    conversation_id: str,
    *,
    tutoring_phase: str,
    struggle_count: int,
    confirm_count: int,
) -> None:
    """Persist a conversation's struggle-escalation phase and counters."""
    async with pool.connection() as conn:
        await conn.execute(
            "update conversations set tutoring_phase = %s, struggle_count = %s, confirm_count = %s "
            "where id = %s",
            (tutoring_phase, struggle_count, confirm_count, conversation_id),
        )


async def get_messages(pool: AsyncConnectionPool, conversation_id: str) -> list[dict]:
    """Return a conversation's messages in order, oldest first."""
    async with pool.connection() as conn:
        async with conn.cursor(row_factory=dict_row) as cur:
            await cur.execute(
                "select role, content from messages where conversation_id = %s order by created_at",
                (conversation_id,),
            )
            return await cur.fetchall()


async def append_message(pool: AsyncConnectionPool, conversation_id: str, role: str, content: str) -> None:
    """Append one message to a conversation."""
    async with pool.connection() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                "insert into messages (conversation_id, role, content) values (%s, %s, %s)",
                (conversation_id, role, content),
            )
        await conn.execute(
            "update conversations set updated_at = now() where id = %s", (conversation_id,)
        )


async def record_flagged_interaction(
    pool: AsyncConnectionPool,
    conversation_id: str,
    student_id: str,
    *,
    category: str,
    question: str,
    blocked: bool,
) -> None:
    """Record a content-safety flag (Decision 022), whether or not it was blocked."""
    async with pool.connection() as conn:
        await conn.execute(
            "insert into flagged_interactions (conversation_id, student_id, category, question, blocked) "
            "values (%s, %s, %s, %s, %s)",
            (conversation_id, student_id, category, question, blocked),
        )
