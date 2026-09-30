"""Unit tests for the struggle-escalation state machine (Decision 031)."""

from app.tutoring.escalation import next_state


def test_first_correct_answer_in_guiding_asks_one_more_confirm_question() -> None:
    """A correct answer doesn't immediately explain -- at least one more confirming question first."""
    result = next_state("guiding", struggle_count=0, confirm_count=0, correctness="correct")
    assert result == ("confirm_question", "confirming", 0, 1)


def test_second_consecutive_correct_answer_wraps_up() -> None:
    """A second correct answer in a row (the confirming one) wraps up with a full explanation."""
    result = next_state("confirming", struggle_count=0, confirm_count=1, correctness="correct")
    assert result == ("confirm_wrapup", "guiding", 0, 0)


def test_unclear_answer_in_guiding_counts_as_struggle() -> None:
    """An unclear (non-)answer is treated the same as a wrong one -- it isn't progress either."""
    result = next_state("guiding", struggle_count=1, confirm_count=0, correctness="unclear")
    assert result == ("guiding", "guiding", 2, 0)


def test_incorrect_answer_below_threshold_keeps_guiding() -> None:
    """The first two incorrect answers just increment the count and keep hinting."""
    result = next_state("guiding", struggle_count=1, confirm_count=0, correctness="incorrect")
    assert result == ("guiding", "guiding", 2, 0)


def test_third_incorrect_answer_escalates_to_explain() -> None:
    """The third consecutive incorrect answer switches to explain-then-confirm."""
    result = next_state("guiding", struggle_count=2, confirm_count=0, correctness="incorrect")
    assert result == ("explain", "confirming", 0, 0)


def test_third_unclear_answer_also_escalates_to_explain() -> None:
    """Three vague non-answers in a row escalate exactly like three wrong ones would."""
    result = next_state("guiding", struggle_count=2, confirm_count=0, correctness="unclear")
    assert result == ("explain", "confirming", 0, 0)


def test_wrong_confirm_answer_retries_but_still_counts_as_struggle() -> None:
    """Getting the confirm question wrong doesn't loop forever -- it shares the same struggle budget."""
    result = next_state("confirming", struggle_count=0, confirm_count=1, correctness="incorrect")
    assert result == ("confirm_retry", "confirming", 1, 0)


def test_three_wrong_confirm_answers_escalate_to_explain() -> None:
    """The struggle cap applies inside the confirming phase too, not just guiding."""
    result = next_state("confirming", struggle_count=2, confirm_count=1, correctness="incorrect")
    assert result == ("explain", "confirming", 0, 0)


def test_unclear_confirm_answer_also_counts_as_struggle() -> None:
    """An unclear answer during confirming is treated the same as incorrect, not ignored."""
    result = next_state("confirming", struggle_count=0, confirm_count=1, correctness="unclear")
    assert result == ("confirm_retry", "confirming", 1, 0)


def test_a_correct_answer_resets_struggle_count() -> None:
    """Getting one right after a couple of misses clears the struggle count, not just freezes it."""
    result = next_state("guiding", struggle_count=2, confirm_count=0, correctness="correct")
    assert result == ("confirm_question", "confirming", 0, 1)


def test_a_wrong_answer_resets_confirm_count() -> None:
    """A wrong answer mid-confirm breaks the correct streak, not just leaves it frozen."""
    result = next_state("confirming", struggle_count=0, confirm_count=1, correctness="incorrect")
    assert result.confirm_count == 0
