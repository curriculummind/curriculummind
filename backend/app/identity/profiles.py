"""
Profile persistence.

Writes go through this module using the backend's direct database
connection, never through a client-side Supabase call -- consistent
with Decision 010 (all domain reads/writes go through the backend).
"""

import secrets

import psycopg
from psycopg.rows import dict_row
from psycopg_pool import AsyncConnectionPool

from app.identity.models import Profile, ProfileCreate

# Excludes 0/O/1/I -- a class code gets read off a screen and retyped by
# hand by a 11-12 year old, so ambiguous characters are worth avoiding.
_CLASS_CODE_ALPHABET = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"
_CLASS_CODE_LENGTH = 6
_MAX_CLASS_CODE_ATTEMPTS = 5


def _generate_class_code() -> str:
    return "".join(secrets.choice(_CLASS_CODE_ALPHABET) for _ in range(_CLASS_CODE_LENGTH))


async def get_teacher_id_by_class_code(pool: AsyncConnectionPool, class_code: str) -> str | None:
    """Look up a teacher's profile id by their class code, or None if no teacher has it."""
    async with pool.connection() as conn:
        async with conn.cursor(row_factory=dict_row) as cur:
            await cur.execute(
                "select id from profiles where role = 'teacher' and class_code = %s",
                (class_code,),
            )
            row = await cur.fetchone()
    return str(row["id"]) if row else None


async def create_profile(
    pool: AsyncConnectionPool, user_id: str, data: ProfileCreate, *, teacher_id: str | None = None
) -> Profile:
    """
    Insert a profile row for a newly signed-up user.

    A teacher gets a freshly generated, unique class_code (Decision
    024). A student is required to have already redeemed one (the
    router resolves class_code to teacher_id before calling this), and
    their profile row plus the resulting guardian_links row are
    inserted together in one connection block -- psycopg's implicit
    per-connection transaction (autocommit is off) means both commit
    together or neither does, the same guarantee this function already
    relied on for its single insert.
    """
    if data.role == "teacher":
        async with pool.connection() as conn:
            for attempt in range(_MAX_CLASS_CODE_ATTEMPTS):
                code = _generate_class_code()
                try:
                    async with conn.cursor(row_factory=dict_row) as cur:
                        await cur.execute(
                            "insert into profiles (id, role, display_name, grade_level, class_code) "
                            "values (%s, %s, %s, %s, %s) "
                            "returning id, role, display_name, grade_level, class_code",
                            (user_id, data.role, data.display_name, data.grade_level, code),
                        )
                        row = await cur.fetchone()
                    break
                except psycopg.errors.UniqueViolation:
                    await conn.rollback()
                    if attempt == _MAX_CLASS_CODE_ATTEMPTS - 1:
                        raise
        return Profile(**{**row, "id": str(row["id"])})

    async with pool.connection() as conn:
        async with conn.cursor(row_factory=dict_row) as cur:
            await cur.execute(
                "insert into profiles (id, role, display_name, grade_level) "
                "values (%s, %s, %s, %s) returning id, role, display_name, grade_level, class_code",
                (user_id, data.role, data.display_name, data.grade_level),
            )
            row = await cur.fetchone()
        if teacher_id is not None:
            await conn.execute(
                "insert into guardian_links (guardian_id, student_id, status) values (%s, %s, 'active')",
                (teacher_id, user_id),
            )
    return Profile(**{**row, "id": str(row["id"])})


async def get_profile(pool: AsyncConnectionPool, user_id: str) -> Profile | None:
    """Fetch a profile by user id, or None if it doesn't exist yet."""
    async with pool.connection() as conn:
        async with conn.cursor(row_factory=dict_row) as cur:
            await cur.execute(
                "select id, role, display_name, grade_level, class_code from profiles where id = %s",
                (user_id,),
            )
            row = await cur.fetchone()
    return Profile(**{**row, "id": str(row["id"])}) if row else None
