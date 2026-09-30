"""
Struggle-escalation state machine (Decision 019, redesigned by Decision 031).

A pure decision function, deliberately separate from the LLM
classification call in correctness.py: given a conversation's current
tutoring phase/counters and the correctness judgment for the student's
latest answer, decides which generation strategy to use next and what
the conversation's new phase/counters should be. Kept pure and
side-effect-free so the state transitions are testable directly,
without a database or an LLM.

Two independent, symmetric counters, checked on every turn regardless
of phase:
- struggle_count: consecutive non-correct answers (incorrect OR
  unclear -- a shrug is not progress any more than a wrong answer is).
  Resets to 0 on any correct answer. Hits STRUGGLE_THRESHOLD -> explain
  directly, no matter which phase it happened in.
- confirm_count: consecutive correct answers. Resets to 0 on any
  non-correct answer. Hits CONFIRM_THRESHOLD -> wrap up with a full
  explanation. CONFIRM_THRESHOLD is 2, not 1, so a single lucky first
  answer doesn't immediately explain -- at least one more confirming
  question is asked first.

The original version of this function let a correct answer in the
"guiding" phase just reset struggle_count and loop in "guiding"
forever -- there was no path from "the student is answering correctly"
to "now explain," only from "the student is answering incorrectly."
An "unclear" answer didn't move either counter, so a student who kept
answering vaguely also never escalated. And once in "confirming",
a wrong confirm answer always returned "confirm_retry" with no cap at
all, so that loop had no exit either. All three were the same class of
bug: escalation only had power to change state via incorrect answers
in the guiding phase, no other case ever ended the pattern. Reported
directly, from a real 15-turn conversation that never once reached an
explanation. Fixed by making struggle and confirm progress independent
of phase and of each other.
"""

from typing import Literal, NamedTuple

Phase = Literal["guiding", "confirming"]
Strategy = Literal["guiding", "explain", "confirm_question", "confirm_retry", "confirm_wrapup"]
Correctness = Literal["correct", "incorrect", "unclear"]

STRUGGLE_THRESHOLD = 3
CONFIRM_THRESHOLD = 2


class EscalationResult(NamedTuple):
    """The chosen generation strategy and the conversation's updated tutoring state."""

    strategy: Strategy
    phase: Phase
    struggle_count: int
    confirm_count: int


def next_state(phase: Phase, struggle_count: int, confirm_count: int, correctness: Correctness) -> EscalationResult:
    """Decide the next generation strategy and tutoring state from the current state and a correctness judgment."""
    if correctness != "correct":
        struggle_count += 1
        if struggle_count >= STRUGGLE_THRESHOLD:
            return EscalationResult("explain", "confirming", 0, 0)
        strategy: Strategy = "guiding" if phase == "guiding" else "confirm_retry"
        return EscalationResult(strategy, phase, struggle_count, 0)

    confirm_count += 1
    if confirm_count >= CONFIRM_THRESHOLD:
        return EscalationResult("confirm_wrapup", "guiding", 0, 0)
    return EscalationResult("confirm_question", "confirming", 0, confirm_count)
