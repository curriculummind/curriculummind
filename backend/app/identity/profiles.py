"""
Profile persistence.

Writes go through this module using the backend's direct database
connection, never through a client-side Supabase call -- consistent
with Decision 010 (all domain reads/writes go through the backend).
"""

from psycopg.rows import dict_row
from psycopg_pool import AsyncConnectionPool

from app.identity.models import Profile, ProfileCreate


async def create_profile(pool: AsyncConnectionPool, user_id: str, data: ProfileCreate) -> Profile:
    """Insert a profile row for a newly signed-up user."""
    async with pool.connection() as conn:
        async with conn.cursor(row_factory=dict_row) as cur:
            await cur.execute(
                "insert into profiles (id, role, display_name, grade_level) "
                "values (%s, %s, %s, %s) returning id, role, display_name, grade_level",
                (user_id, data.role, data.display_name, data.grade_level),
            )
            row = await cur.fetchone()
    return Profile(**{**row, "id": str(row["id"])})


async def get_profile(pool: AsyncConnectionPool, user_id: str) -> Profile | None:
    """Fetch a profile by user id, or None if it doesn't exist yet."""
    async with pool.connection() as conn:
        async with conn.cursor(row_factory=dict_row) as cur:
            await cur.execute(
                "select id, role, display_name, grade_level from profiles where id = %s",
                (user_id,),
            )
            row = await cur.fetchone()
    return Profile(**{**row, "id": str(row["id"])}) if row else None
