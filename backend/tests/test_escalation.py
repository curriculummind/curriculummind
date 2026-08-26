"""Unit tests for the struggle-escalation state machine."""

from app.tutoring.escalation import next_state


def test_correct_answer_in_guiding_resets_struggle_count() -> None:
    """A correct answer while guiding resets the struggle count and keeps guiding."""
    result = next_state("guiding", struggle_count=2, confirm_count=0, correctness="correct")
    assert result == ("guiding", "guiding", 0, 0)


def test_unclear_answer_in_guiding_leaves_struggle_count_unchanged() -> None:
    """An unclear answer isn't a wrong attempt, so the struggle count doesn't move."""
    result = next_state("guiding", struggle_count=1, confirm_count=0, correctness="unclear")
    assert result == ("guiding", "guiding", 1, 0)


def test_incorrect_answer_below_threshold_keeps_guiding() -> None:
    """The first two incorrect answers just increment the count and keep hinting."""
    result = next_state("guiding", struggle_count=1, confirm_count=0, correctness="incorrect")
    assert result == ("guiding", "guiding", 2, 0)


def test_third_incorrect_answer_escalates_to_explain() -> None:
    """The third consecutive incorrect answer switches to explain-then-confirm."""
    result = next_state("guiding", struggle_count=2, confirm_count=0, correctness="incorrect")
    assert result == ("explain", "confirming", 0, 0)


def test_correct_confirm_answer_below_threshold_asks_next_confirm_question() -> None:
    """A correct confirm answer below the threshold asks another confirm question."""
    result = next_state("confirming", struggle_count=0, confirm_count=1, correctness="correct")
    assert result == ("confirm_question", "confirming", 0, 2)


def test_third_correct_confirm_answer_wraps_up() -> None:
    """The third correct confirm answer wraps up and returns to guiding."""
    result = next_state("confirming", struggle_count=0, confirm_count=2, correctness="correct")
    assert result == ("confirm_wrapup", "guiding", 0, 0)


def test_incorrect_confirm_answer_retries_without_changing_counters() -> None:
    """An incorrect confirm answer re-explains and retries without advancing the count."""
    result = next_state("confirming", struggle_count=0, confirm_count=1, correctness="incorrect")
    assert result == ("confirm_retry", "confirming", 0, 1)


def test_unclear_confirm_answer_also_retries() -> None:
    """An unclear confirm answer is treated the same as incorrect -- retry, don't advance."""
    result = next_state("confirming", struggle_count=0, confirm_count=1, correctness="unclear")
    assert result == ("confirm_retry", "confirming", 0, 1)
