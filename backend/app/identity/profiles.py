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

# Excludes 0/O/1/I -- a class code (or a student's link code, Decision
# 034, generated the same way) gets read off a screen and retyped by
# hand by a 11-12 year old, so ambiguous characters are worth avoiding.
_CLASS_CODE_ALPHABET = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"
_CLASS_CODE_LENGTH = 6
_MAX_CLASS_CODE_ATTEMPTS = 5


def _generate_short_code() -> str:
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


async def get_student_id_by_link_code(pool: AsyncConnectionPool, student_link_code: str) -> str | None:
    """Look up a student's profile id by their link code, or None if no student has it."""
    async with pool.connection() as conn:
        async with conn.cursor(row_factory=dict_row) as cur:
            await cur.execute(
                "select id from profiles where role = 'student' and student_link_code = %s",
                (student_link_code,),
            )
            row = await cur.fetchone()
    return str(row["id"]) if row else None


_PROFILE_COLUMNS = "id, role, display_name, grade_level, class_code, student_link_code, subscription_status"


async def create_profile(
    pool: AsyncConnectionPool,
    user_id: str,
    data: ProfileCreate,
    *,
    teacher_id: str | None = None,
    student_id: str | None = None,
) -> Profile:
    """
    Insert a profile row for a newly signed-up user.

    A teacher gets a freshly generated, unique class_code (Decision
    024); a student gets a freshly generated, unique student_link_code
    the same way (Decision 034) -- both use the same retry-on-
    UniqueViolation loop, since both are drawn from the same alphabet
    and can collide the same way. A guardian (parent) is required to
    have already redeemed a student's link code (the router resolves it
    to student_id before calling this) exactly as a student today must
    already have redeemed a teacher's class_code -- the two flows are
    mirror images, just with guardian_id and student_id swapped in the
    resulting guardian_links row. Profile + guardian_links inserts
    happen together in one connection block -- psycopg's implicit
    per-connection transaction (autocommit is off) means both commit
    together or neither does.
    """
    if data.role == "teacher":
        async with pool.connection() as conn:
            for attempt in range(_MAX_CLASS_CODE_ATTEMPTS):
                code = _generate_short_code()
                try:
                    async with conn.cursor(row_factory=dict_row) as cur:
                        await cur.execute(
                            "insert into profiles (id, role, display_name, grade_level, class_code) "
                            f"values (%s, %s, %s, %s, %s) returning {_PROFILE_COLUMNS}",
                            (user_id, data.role, data.display_name, data.grade_level, code),
                        )
                        row = await cur.fetchone()
                    break
                except psycopg.errors.UniqueViolation:
                    await conn.rollback()
                    if attempt == _MAX_CLASS_CODE_ATTEMPTS - 1:
                        raise
        return Profile(**{**row, "id": str(row["id"])})

    if data.role == "student":
        async with pool.connection() as conn:
            for attempt in range(_MAX_CLASS_CODE_ATTEMPTS):
                code = _generate_short_code()
                try:
                    async with conn.cursor(row_factory=dict_row) as cur:
                        await cur.execute(
                            "insert into profiles (id, role, display_name, grade_level, student_link_code) "
                            f"values (%s, %s, %s, %s, %s) returning {_PROFILE_COLUMNS}",
                            (user_id, data.role, data.display_name, data.grade_level, code),
                        )
                        row = await cur.fetchone()
                    break
                except psycopg.errors.UniqueViolation:
                    await conn.rollback()
                    if attempt == _MAX_CLASS_CODE_ATTEMPTS - 1:
                        raise
            if teacher_id is not None:
                await conn.execute(
                    "insert into guardian_links (guardian_id, student_id, status) values (%s, %s, 'active')",
                    (teacher_id, user_id),
                )
        return Profile(**{**row, "id": str(row["id"])})

    async with pool.connection() as conn:
        async with conn.cursor(row_factory=dict_row) as cur:
            await cur.execute(
                "insert into profiles (id, role, display_name, grade_level) "
                f"values (%s, %s, %s, %s) returning {_PROFILE_COLUMNS}",
                (user_id, data.role, data.display_name, data.grade_level),
            )
            row = await cur.fetchone()
        if student_id is not None:
            await conn.execute(
                "insert into guardian_links (guardian_id, student_id, status) values (%s, %s, 'active')",
                (user_id, student_id),
            )
    return Profile(**{**row, "id": str(row["id"])})


async def get_profile(pool: AsyncConnectionPool, user_id: str) -> Profile | None:
    """Fetch a profile by user id, or None if it doesn't exist yet."""
    async with pool.connection() as conn:
        async with conn.cursor(row_factory=dict_row) as cur:
            await cur.execute(
                f"select {_PROFILE_COLUMNS} from profiles where id = %s",
                (user_id,),
            )
            row = await cur.fetchone()
    return Profile(**{**row, "id": str(row["id"])}) if row else None
