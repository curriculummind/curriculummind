"""
Per-topic mastery aggregation (Pillar C-M, pulled forward for the chat
sidebar's topic chart).

Every turn's raw outcome is already recorded in `decision_traces`
(Decision 023), but nothing rolls it up into "how is this student doing
on this topic" -- that's what this module computes, on demand, per
request. No new tracking, just aggregation of what's already there.

Mastery tier is based on the trailing streak of consecutive correct
answers on a topic, not a single lucky guess: getting one question
right proves nothing on its own, but three in a row is a real signal.

- streak of 3+ consecutive correct answers -> mastery
- most recent answer correct, streak under 3 -> learning
- most recent answer incorrect or unclear   -> needs practice
- no resolved attempts at all               -> not started (None)

This is deliberately a first cut, not the full definition: it doesn't
yet weight by question difficulty, or require the streak to hold up
over time (e.g. across a couple of weeks, to show real retention
rather than a good day). Both were raised as the right long-term
definition of mastery and are real future scope (spaced review),
not something this data supports yet -- there's no difficulty tagging
on content, and no mechanism prompting a student to revisit a topic
later to re-test retention.
"""

import re
from typing import Literal

from psycopg.rows import dict_row
from psycopg_pool import AsyncConnectionPool
from pydantic import BaseModel

Tier = Literal["mastery", "learning", "needs-practice"]

MASTERY_STREAK = 3

_MODULE_NUMBER = re.compile(r"Module\s+(\d+)")
_TOPIC_LETTER = re.compile(r"Topic\s+([A-Z]):\s*(.+?)(?:\s*\(Teacher Edition\))?\s*$")


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
    # everything after the first ": " is the actual chapter name. (A
    # single-token regex prefix match was tried first and silently did
    # nothing, since the real prefix is a multi-word phrase, not one
    # token -- caught only because the rendered name still showed the
    # full "CK-12 Life Science for Middle School: " prefix live.)
    _, _, rest = title.partition(": ")
    return None, rest or title


def _tier_for(correctness_sequence: list[str]) -> Tier | None:
    """Classify a topic's tier from its oldest-to-newest sequence of resolved answers."""
    if not correctness_sequence:
        return None
    if correctness_sequence[-1] != "correct":
        return "needs-practice"
    streak = 0
    for outcome in reversed(correctness_sequence):
        if outcome != "correct":
            break
        streak += 1
    return "mastery" if streak >= MASTERY_STREAK else "learning"


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
            dt.correctness,
            dt.created_at
        from curriculum_resources cr
        join concepts c on c.id = cr.concept_id
        join subjects s on s.id = c.subject_id
        left join lateral (
            select dt2.correctness, dt2.created_at
            from decision_traces dt2
            where dt2.correctness is not null
                and dt2.student_id = %(student_id)s
                and exists (
                    select 1 from document_chunks dc2
                    where dc2.id = any(dt2.evidence_chunk_ids) and dc2.resource_id = cr.id
                )
        ) dt on true
        where s.slug = %(subject_slug)s and c.grade_band = %(grade_band)s
        order by c.name, cr.title, dt.created_at asc
    """
    async with pool.connection() as conn:
        async with conn.cursor(row_factory=dict_row) as cur:
            await cur.execute(query, {"student_id": student_id, "subject_slug": subject_slug, "grade_band": grade_band})
            rows = await cur.fetchall()

    modules: dict[str, Module] = {}
    sequences: dict[str, list[str]] = {}
    topic_meta: dict[str, tuple[str, str | None, str]] = {}  # resource_id -> (concept_id, letter, name)

    for row in rows:
        concept_id = str(row["concept_id"])
        resource_id = str(row["resource_id"])
        if concept_id not in modules:
            modules[concept_id] = Module(
                concept_id=concept_id,
                name=row["module_name"],
                module_number=_parse_module_number(row["title"]),
                topics=[],
            )
        if resource_id not in sequences:
            sequences[resource_id] = []
            letter, name = _parse_topic(row["title"])
            topic_meta[resource_id] = (concept_id, letter, name)
        if row["correctness"] is not None:
            sequences[resource_id].append(row["correctness"])

    for resource_id, (concept_id, letter, name) in topic_meta.items():
        modules[concept_id].topics.append(
            Topic(resource_id=resource_id, letter=letter, name=name, tier=_tier_for(sequences[resource_id]))
        )

    return sorted(modules.values(), key=lambda m: (m.module_number is None, m.module_number or 0, m.name))
