"""Unit tests for per-topic mastery tier classification."""

from app.tutoring.progress import _tier_for


def test_no_attempts_is_not_started() -> None:
    """An empty correctness sequence means the topic hasn't been touched yet."""
    assert _tier_for([]) is None


def test_single_correct_answer_is_learning_not_mastery() -> None:
    """One correct answer alone doesn't prove understanding -- it's learning, not mastery."""
    assert _tier_for(["correct"]) == "learning"


def test_two_consecutive_correct_answers_is_still_learning() -> None:
    """A streak under the mastery threshold stays learning."""
    assert _tier_for(["correct", "correct"]) == "learning"


def test_three_consecutive_correct_answers_is_mastery() -> None:
    """Three correct answers in a row is the real mastery signal."""
    assert _tier_for(["correct", "correct", "correct"]) == "mastery"


def test_streak_must_be_consecutive_and_current() -> None:
    """An older streak broken by a recent miss doesn't count -- only the trailing streak matters."""
    assert _tier_for(["correct", "correct", "correct", "incorrect", "correct"]) == "learning"


def test_most_recent_incorrect_is_needs_practice_regardless_of_history() -> None:
    """A student currently getting it wrong reads as needs-practice even after past mastery."""
    assert _tier_for(["correct", "correct", "correct", "incorrect"]) == "needs-practice"


def test_most_recent_unclear_is_needs_practice() -> None:
    """An unclear (non-answer) response is treated the same as incorrect, not ignored."""
    assert _tier_for(["correct", "unclear"]) == "needs-practice"
