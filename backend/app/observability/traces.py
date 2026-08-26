"""
Decision-trace persistence (Decision 023).

Writes the tutoring pipeline's own per-turn decisions -- safety
category, retrieval band, chosen strategy, the evidence actually used,
assignment/correctness flags, and the escalation state transition -- as
a byproduct of the request that already computed all of it. No new
judgment happens here; every value this writes was already sitting in
the LangGraph state or the router's local variables and was being
discarded the moment the response finished streaming.
"""

from psycopg_pool import AsyncConnectionPool


async def record_decision_trace(
    pool: AsyncConnectionPool,
    conversation_id: str,
    student_id: str,
    *,
    question: str,
    safety_category: str,
    band: str | None,
    strategy: str | None,
    is_assignment: bool | None,
    evidence_chunk_ids: list[str],
    correctness: str | None,
    tutoring_phase_before: str,
    tutoring_phase_after: str,
    struggle_count_before: int,
    struggle_count_after: int,
    confirm_count_before: int,
    confirm_count_after: int,
) -> None:
    """Persist one turn's tutoring decision. Admin-only -- never exposed to students or guardians."""
    async with pool.connection() as conn:
        await conn.execute(
            """
            insert into decision_traces (
                conversation_id, student_id, question, safety_category, band, strategy,
                is_assignment, evidence_chunk_ids, correctness,
                tutoring_phase_before, tutoring_phase_after,
                struggle_count_before, struggle_count_after,
                confirm_count_before, confirm_count_after
            ) values (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """,
            (
                conversation_id,
                student_id,
                question,
                safety_category,
                band,
                strategy,
                is_assignment,
                evidence_chunk_ids,
                correctness,
                tutoring_phase_before,
                tutoring_phase_after,
                struggle_count_before,
                struggle_count_after,
                confirm_count_before,
                confirm_count_after,
            ),
        )
