"""
Per-topic mastery aggregation (Pillar C-M, pulled forward for the chat
sidebar's topic chart).

Every turn's raw outcome is already recorded in `decision_traces`
(Decision 023), but nothing rolls it up into "how is this student doing
on this topic" -- that's what this module computes, on demand, per
request. No new tracking, just aggregation of what's already there.

Mastery tier is derived from a fact already implicit in the escalation
state machine (`app/tutoring/escalation.py`): `struggle_count` resets to
0 the instant a correct answer lands during the "guiding" phase, so at
that moment `struggle_count_before + 1` is exactly how many attempts
that correct answer took.

- 1 attempt  -> mastery
- 2 attempts -> learning
- 3+ attempts, or the answer came during the post-explain "confirming"
  phase at all (which only happens after 3+ guiding-phase struggles) ->
  needs practice

The tier shown per topic is the most recent solved instance, not an
average -- a student who struggled early and now gets it right reads as
improving, not stuck.
"""

import re
from typing import Literal

from psycopg.rows import dict_row
from psycopg_pool import AsyncConnectionPool
from pydantic import BaseModel

Tier = Literal["mastery", "learning", "needs-practice"]

_MODULE_NUMBER = re.compile(r"Module\s+(\d+)")
_TOPIC_LETTER = re.compile(r"Topic\s+([A-Z]):\s*(.+?)(?:\s*\(Teacher Edition\))?\s*$")
_SOURCE_PREFIX = re.compile(r"^[\w-]+(?: \d+)?:\s*")


def _parse_module_number(title: str) -> int | None:
    match = _MODULE_NUMBER.search(title)
    return int(match.group(1)) if match else None


def _parse_topic(title: str) -> tuple[str | None, str]:
    """Return (topic letter, short name) from a resource title, math-style or not."""
    match = _TOPIC_LETTER.search(title)
    if match:
        return match.group(1), match.group(2)
    # Science resources are one chapter-length resource per concept, titled
    # e.g. "CK-12 Life Science for Middle School: Human Body Systems" --
    # strip the source-name prefix and use the rest as the topic name.
    stripped = _SOURCE_PREFIX.sub("", title, count=1)
    return None, stripped


def _tier_for(struggle_count_before: int | None, tutoring_phase_before: str | None) -> Tier | None:
    if tutoring_phase_before is None:
        return None
    if tutoring_phase_before == "confirming":
        return "needs-practice"
    attempts = (struggle_count_before or 0) + 1
    if attempts == 1:
        return "mastery"
    if attempts == 2:
        return "learning"
    return "needs-practice"


class Topic(BaseModel):
    resource_id: str
    letter: str | None
    name: str
    tier: Tier | None


class Module(BaseModel):
    concept_id: str
    name: str
    module_number: int | None
    topics: list[Topic]


async def get_topic_progress(
    pool: AsyncConnectionPool, student_id: str, *, subject_slug: str, grade_band: str
) -> list[Module]:
    """Every topic in a subject/grade band, with this student's current mastery tier on each."""
    query = """
        select
            c.id as concept_id,
            c.name as module_name,
            cr.id as resource_id,
            cr.title,
            dt.struggle_count_before,
            dt.tutoring_phase_before
        from curriculum_resources cr
        join concepts c on c.id = cr.concept_id
        join subjects s on s.id = c.subject_id
        left join lateral (
            select dt2.struggle_count_before, dt2.tutoring_phase_before, dt2.created_at
            from decision_traces dt2
            join document_chunks dc2
                on dc2.id = any(dt2.evidence_chunk_ids) and dc2.resource_id = cr.id
            where dt2.correctness = 'correct' and dt2.student_id = %(student_id)s
            order by dt2.created_at desc
            limit 1
        ) dt on true
        where s.slug = %(subject_slug)s and c.grade_band = %(grade_band)s
        order by c.name, cr.title
    """
    async with pool.connection() as conn:
        async with conn.cursor(row_factory=dict_row) as cur:
            await cur.execute(query, {"student_id": student_id, "subject_slug": subject_slug, "grade_band": grade_band})
            rows = await cur.fetchall()

    modules: dict[str, Module] = {}
    for row in rows:
        concept_id = str(row["concept_id"])
        if concept_id not in modules:
            modules[concept_id] = Module(
                concept_id=concept_id,
                name=row["module_name"],
                module_number=_parse_module_number(row["title"]),
                topics=[],
            )
        letter, name = _parse_topic(row["title"])
        modules[concept_id].topics.append(
            Topic(
                resource_id=str(row["resource_id"]),
                letter=letter,
                name=name,
                tier=_tier_for(row["struggle_count_before"], row["tutoring_phase_before"]),
            )
        )

    return sorted(modules.values(), key=lambda m: (m.module_number is None, m.module_number or 0, m.name))
