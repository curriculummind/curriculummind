"""
Struggle-escalation state machine (Decision 019).

A pure decision function, deliberately separate from the LLM
classification call in correctness.py: given a conversation's current
tutoring phase/counters and the correctness judgment for the student's
latest answer, decides which generation strategy to use next and what
the conversation's new phase/counters should be. Kept pure and
side-effect-free so the state transitions are testable directly,
without a database or an LLM.
"""

from typing import Literal, NamedTuple

Phase = Literal["guiding", "confirming"]
Strategy = Literal["guiding", "explain", "confirm_question", "confirm_retry", "confirm_wrapup"]
Correctness = Literal["correct", "incorrect", "unclear"]

STRUGGLE_THRESHOLD = 3
CONFIRM_THRESHOLD = 3


class EscalationResult(NamedTuple):
    """The chosen generation strategy and the conversation's updated tutoring state."""

    strategy: Strategy
    phase: Phase
    struggle_count: int
    confirm_count: int


def next_state(phase: Phase, struggle_count: int, confirm_count: int, correctness: Correctness) -> EscalationResult:
    """Decide the next generation strategy and tutoring state from the current state and a correctness judgment."""
    if phase == "guiding":
        if correctness == "correct":
            return EscalationResult("guiding", "guiding", 0, confirm_count)
        if correctness == "unclear":
            return EscalationResult("guiding", "guiding", struggle_count, confirm_count)
        struggle_count += 1
        if struggle_count >= STRUGGLE_THRESHOLD:
            return EscalationResult("explain", "confirming", 0, 0)
        return EscalationResult("guiding", "guiding", struggle_count, confirm_count)

    if correctness != "correct":
        return EscalationResult("confirm_retry", "confirming", struggle_count, confirm_count)
    confirm_count += 1
    if confirm_count >= CONFIRM_THRESHOLD:
        return EscalationResult("confirm_wrapup", "guiding", 0, 0)
    return EscalationResult("confirm_question", "confirming", struggle_count, confirm_count)
