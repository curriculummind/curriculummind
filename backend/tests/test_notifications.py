"""Unit tests for notification crossing-detection (Decision 025)."""

from app.evaluation.notifications import (
    _assignment_pattern_crossed,
    _mastery_milestone_crossed,
    _repeated_struggle_crossed,
    _trailing_streak,
)


def test_trailing_streak_on_empty_sequence_is_zero() -> None:
    assert _trailing_streak([], lambda x: x == "correct") == 0


def test_trailing_streak_stops_at_first_non_match_from_the_end() -> None:
    assert _trailing_streak(["correct", "incorrect", "correct", "correct"], lambda x: x == "correct") == 2


def test_mastery_milestone_does_not_fire_under_threshold() -> None:
    assert _mastery_milestone_crossed(["correct", "correct"]) is False


def test_mastery_milestone_fires_exactly_at_threshold() -> None:
    assert _mastery_milestone_crossed(["correct", "correct", "correct"]) is True


def test_mastery_milestone_does_not_refire_past_threshold() -> None:
    """A 4th consecutive correct answer shouldn't re-fire the same alert every turn."""
    assert _mastery_milestone_crossed(["correct", "correct", "correct", "correct"]) is False


def test_mastery_milestone_fires_again_after_a_broken_and_rebuilt_streak() -> None:
    """Unlike the cumulative growth curve, a live alert should fire again on a fresh climb back to 3."""
    sequence = ["correct", "correct", "correct", "incorrect", "correct", "correct", "correct"]
    assert _mastery_milestone_crossed(sequence) is True


def test_repeated_struggle_fires_exactly_at_threshold() -> None:
    assert _repeated_struggle_crossed(["incorrect", "unclear", "incorrect"]) is True


def test_repeated_struggle_does_not_fire_under_threshold() -> None:
    assert _repeated_struggle_crossed(["correct", "incorrect", "unclear"]) is False


def test_repeated_struggle_does_not_refire_past_threshold() -> None:
    assert _repeated_struggle_crossed(["incorrect", "incorrect", "incorrect", "unclear"]) is False


def test_assignment_pattern_fires_exactly_at_threshold() -> None:
    assert _assignment_pattern_crossed([True, True, True]) is True


def test_assignment_pattern_interrupted_by_none_does_not_fire() -> None:
    """A safety-blocked turn (is_assignment=None) should interrupt the streak, not be ignored."""
    assert _assignment_pattern_crossed([True, None, True, True]) is False


def test_assignment_pattern_interrupted_by_false_does_not_fire() -> None:
    assert _assignment_pattern_crossed([True, True, False, True, True]) is False
