"""
Event-driven, in-app-only guardian notifications (Decision 025).

Runs in-process via a FastAPI BackgroundTask scheduled at the end of
/tutor/ask, right after record_decision_trace persists the turn --
async relative to the streamed response, but not a separate worker
process (none exists in this codebase yet; see this module's package
docstring). Reads only decision_traces, which already has every field
needed with zero new instrumentation, same as app/tutoring/progress.py.

Four categories, each computed independently for the student's single
latest turn:

- mastery_milestone: a topic's trailing correct-answer streak just
  crossed exactly MASTERY_STREAK on this turn.
- repeated_struggle: the same topic's trailing wrong/unclear streak
  just crossed exactly 3 on this turn -- a simplified proxy for "stuck
  across repeated attempts," not real session boundaries.
- assignment_pattern: the student's last 3 turns were all flagged as
  assignment-like, topic-agnostic.
- sensitive_topic: any non-"none" safety_category on this turn, fires
  immediately (no streak -- a single occurrence is inherently worth a
  guardian's attention, per the same reasoning behind Decision 022).

Crossing detection (equality, not >=) is deliberate: without it, every
turn after the threshold would re-fire the same alert. This is why
progress.py's _mastery_achieved_at isn't reused directly here -- it
answers "when was mastery FIRST ever achieved" for a cumulative growth
curve, not "did this specific turn just cross the line," which is what
a live alert needs (including firing again after a later regression
and a fresh climb back to a streak of 3).
"""

from collections.abc import Callable
from typing import TypeVar

from psycopg.rows import dict_row
from psycopg_pool import AsyncConnectionPool

from app.tutoring.progress import MASTERY_STREAK, _parse_topic

_STRUGGLE_STREAK = 3
_ASSIGNMENT_PATTERN_STREAK = 3

# Per-safety_category message wording (Decision 022's categories). All of
# these are stored under the single "sensitive_topic" notifications.category
# (for icon/styling purposes), but the wording must not be one-size-fits-all
# -- a crisis flag is a materially different event for a guardian to read
# than an ordinary sensitive-topic hit, and should read that way.
_SAFETY_MESSAGES: dict[str, str] = {
    "crisis": (
        "The tutor noticed language suggesting {name} may be in crisis during a recent "
        "session. Please check in as soon as you can."
    ),
    "sensitive_topic": "A sensitive topic came up during {name}'s session today.",
    "pii": "{name} shared what looked like personal information during a session.",
    "prompt_injection": "{name}'s session included an attempt to manipulate the tutor's instructions.",
    "unsafe_content": "{name}'s session touched on unsafe content that was declined.",
}

T = TypeVar("T")


def _trailing_streak(sequence: list[T], matches: Callable[[T], bool]) -> int:
    """Count trailing entries (most recent first) satisfying `matches`, stopping at the first that doesn't."""
    streak = 0
    for item in reversed(sequence):
        if not matches(item):
            break
        streak += 1
    return streak


def _mastery_milestone_crossed(correctness_sequence: list[str]) -> bool:
    return _trailing_streak(correctness_sequence, lambda c: c == "correct") == MASTERY_STREAK


def _repeated_struggle_crossed(correctness_sequence: list[str]) -> bool:
    return _trailing_streak(correctness_sequence, lambda c: c in ("incorrect", "unclear")) == _STRUGGLE_STREAK


def _assignment_pattern_crossed(is_assignment_sequence: list[bool | None]) -> bool:
    return _trailing_streak(is_assignment_sequence, lambda a: a is True) == _ASSIGNMENT_PATTERN_STREAK


async def _record(pool: AsyncConnectionPool, student_id: str, category: str, message: str) -> None:
    async with pool.connection() as conn:
        await conn.execute(
            "insert into notifications (student_id, category, message) values (%s, %s, %s)",
            (student_id, category, message),
        )


async def detect_and_record_notifications(pool: AsyncConnectionPool, student_id: str) -> None:
    """Evaluate all four notification triggers against a student's latest turn and record any that just fired."""
    async with pool.connection() as conn:
        async with conn.cursor(row_factory=dict_row) as cur:
            await cur.execute(
                "select display_name from profiles where id = %s",
                (student_id,),
            )
            profile_row = await cur.fetchone()
            await cur.execute(
                "select safety_category, is_assignment, evidence_chunk_ids "
                "from decision_traces where student_id = %s order by created_at desc limit 1",
                (student_id,),
            )
            latest = await cur.fetchone()

    if latest is None:
        return
    display_name = profile_row["display_name"] if profile_row else "This student"

    if latest["safety_category"] and latest["safety_category"] != "none":
        template = _SAFETY_MESSAGES.get(latest["safety_category"], _SAFETY_MESSAGES["sensitive_topic"])
        await _record(pool, student_id, "sensitive_topic", template.format(name=display_name))

    async with pool.connection() as conn:
        async with conn.cursor(row_factory=dict_row) as cur:
            await cur.execute(
                "select is_assignment from decision_traces where student_id = %s "
                "order by created_at desc limit %s",
                (student_id, _ASSIGNMENT_PATTERN_STREAK),
            )
            recent = await cur.fetchall()
    is_assignment_sequence = [row["is_assignment"] for row in reversed(recent)]
    if _assignment_pattern_crossed(is_assignment_sequence):
        await _record(
            pool,
            student_id,
            "assignment_pattern",
            f"{display_name} has asked for help on assignment-style questions across the last "
            f"{_ASSIGNMENT_PATTERN_STREAK} turns.",
        )

    evidence_chunk_ids = latest["evidence_chunk_ids"] or []
    if not evidence_chunk_ids:
        return

    async with pool.connection() as conn:
        async with conn.cursor(row_factory=dict_row) as cur:
            await cur.execute(
                "select distinct dc.resource_id, cr.title "
                "from document_chunks dc join curriculum_resources cr on cr.id = dc.resource_id "
                "where dc.id = any(%s)",
                (evidence_chunk_ids,),
            )
            resources = await cur.fetchall()

    for resource in resources:
        async with pool.connection() as conn:
            async with conn.cursor(row_factory=dict_row) as cur:
                await cur.execute(
                    """
                    select correctness from decision_traces
                    where student_id = %(student_id)s
                        and correctness is not null
                        and exists (
                            select 1 from document_chunks dc
                            where dc.id = any(evidence_chunk_ids) and dc.resource_id = %(resource_id)s
                        )
                    order by created_at asc
                    """,
                    {"student_id": student_id, "resource_id": resource["resource_id"]},
                )
                topic_rows = await cur.fetchall()
        correctness_sequence = [row["correctness"] for row in topic_rows]
        _, topic_name = _parse_topic(resource["title"])

        if _mastery_milestone_crossed(correctness_sequence):
            await _record(pool, student_id, "mastery_milestone", f"{display_name} reached mastery on {topic_name}.")
        if _repeated_struggle_crossed(correctness_sequence):
            await _record(
                pool,
                student_id,
                "repeated_struggle",
                f"{display_name} has struggled with {_STRUGGLE_STREAK} questions in a row on {topic_name}.",
            )
