"""Unit tests for class-code validation on profile creation (Decision 024)."""

import pytest
from pydantic import ValidationError

from app.identity.models import ProfileCreate
from app.identity.profiles import _CLASS_CODE_ALPHABET, _CLASS_CODE_LENGTH, _generate_class_code


def test_student_without_class_code_is_rejected() -> None:
    with pytest.raises(ValidationError):
        ProfileCreate(role="student", display_name="Maya", grade_level=6)


def test_student_with_blank_class_code_is_rejected() -> None:
    with pytest.raises(ValidationError):
        ProfileCreate(role="student", display_name="Maya", grade_level=6, class_code="   ")


def test_student_class_code_is_normalized_to_uppercase() -> None:
    profile = ProfileCreate(role="student", display_name="Maya", grade_level=6, class_code=" ab12cd ")
    assert profile.class_code == "AB12CD"


def test_teacher_cannot_set_a_class_code() -> None:
    with pytest.raises(ValidationError):
        ProfileCreate(role="teacher", display_name="Ms. Alvarez", class_code="AB12CD")


def test_teacher_without_class_code_is_valid() -> None:
    profile = ProfileCreate(role="teacher", display_name="Ms. Alvarez")
    assert profile.class_code is None


def test_generated_class_code_has_expected_length_and_alphabet() -> None:
    code = _generate_class_code()
    assert len(code) == _CLASS_CODE_LENGTH
    assert all(char in _CLASS_CODE_ALPHABET for char in code)


def test_class_code_alphabet_excludes_ambiguous_characters() -> None:
    for ambiguous in "0O1I":
        assert ambiguous not in _CLASS_CODE_ALPHABET
