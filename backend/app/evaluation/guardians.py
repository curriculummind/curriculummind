"""
Guardian-facing reads: roster, per-student authorization, notifications.

is_active_guardian_of is the one authorization primitive Decision
009/010 require to be enforced in backend code, not assumed from RLS
alone -- it gates the single-student detail endpoints, the only ones
that take an untrusted student_id as input. The roster and
notifications queries are safe without a separate check because they
scope themselves to the caller's own guardian_links rows in the query
itself, never taking a student_id from the caller.
"""

from datetime import datetime

from psycopg.rows import dict_row
from psycopg_pool import AsyncConnectionPool

from app.evaluation.models import Notification, RosterStudent
from app.tutoring.progress import Tier, get_topic_progress

_TIER_SEVERITY: dict[Tier, int] = {"needs-practice": 0, "learning": 1, "mastery": 2}
_SUBJECTS = ["math", "science"]


async def is_active_guardian_of(pool: AsyncConnectionPool, guardian_id: str, student_id: str) -> bool:
    async with pool.connection() as conn:
        async with conn.cursor(row_factory=dict_row) as cur:
            await cur.execute(
                "select exists(select 1 from guardian_links "
                "where guardian_id = %s and student_id = %s and status = 'active') as linked",
                (guardian_id, student_id),
            )
            row = await cur.fetchone()
    return bool(row["linked"])


async def _list_students_for_guardian(pool: AsyncConnectionPool, guardian_id: str) -> list[dict]:
    async with pool.connection() as conn:
        async with conn.cursor(row_factory=dict_row) as cur:
            await cur.execute(
                "select p.id, p.display_name from guardian_links gl "
                "join profiles p on p.id = gl.student_id "
                "where gl.guardian_id = %s and gl.status = 'active' "
                "order by p.display_name",
                (guardian_id,),
            )
            return await cur.fetchall()


async def _last_active_by_student(pool: AsyncConnectionPool, student_ids: list[str]) -> dict[str, datetime]:
    if not student_ids:
        return {}
    async with pool.connection() as conn:
        async with conn.cursor(row_factory=dict_row) as cur:
            await cur.execute(
                "select student_id, max(created_at) as last_active from decision_traces "
                "where student_id = any(%s) group by student_id",
                (student_ids,),
            )
            rows = await cur.fetchall()
    return {str(row["student_id"]): row["last_active"] for row in rows}


def _summary_tier(modules) -> Tier | None:
    """The single worst tier among a subject's started topics, or None if nothing's been started."""
    tiers = [t.tier for m in modules for t in m.topics if t.tier is not None]
    if not tiers:
        return None
    return min(tiers, key=lambda t: _TIER_SEVERITY[t])


async def build_roster(pool: AsyncConnectionPool, guardian_id: str) -> list[RosterStudent]:
    """
    A teacher's (or, later, a parent's) linked students with a per-
    subject tier summary each. Deliberately a first cut, same tone as
    progress.py's own docstring: this is one get_topic_progress call
    per subject per student (an accepted N+1 for a classroom-sized
    roster), reusing that function directly rather than hand-rolling a
    wider join, since a wider join risks reintroducing the exact
    double-counting bug _fetch_rows's docstring already warns about --
    not worth that risk for a summary view.
    """
    students = await _list_students_for_guardian(pool, guardian_id)
    last_active = await _last_active_by_student(pool, [str(s["id"]) for s in students])

    roster: list[RosterStudent] = []
    for student in students:
        student_id = str(student["id"])
        subject_tiers: dict[str, Tier | None] = {}
        for subject in _SUBJECTS:
            modules = await get_topic_progress(pool, student_id, subject_slug=subject, grade_band="6")
            subject_tiers[subject] = _summary_tier(modules)
        roster.append(
            RosterStudent(
                student_id=student_id,
                display_name=student["display_name"],
                subject_tiers=subject_tiers,
                needs_attention=any(tier == "needs-practice" for tier in subject_tiers.values()),
                last_active=last_active.get(student_id),
            )
        )
    return roster


async def list_notifications_for_guardian(pool: AsyncConnectionPool, guardian_id: str) -> list[Notification]:
    async with pool.connection() as conn:
        async with conn.cursor(row_factory=dict_row) as cur:
            await cur.execute(
                "select n.id, n.student_id, p.display_name as student_display_name, "
                "n.category, n.message, n.created_at "
                "from notifications n "
                "join guardian_links gl on gl.student_id = n.student_id "
                "    and gl.guardian_id = %s and gl.status = 'active' "
                "join profiles p on p.id = n.student_id "
                "order by n.created_at desc limit 50",
                (guardian_id,),
            )
            rows = await cur.fetchall()
    return [Notification(**{**row, "id": str(row["id"]), "student_id": str(row["student_id"])}) for row in rows]
