"""Data shapes for student and guardian profiles."""

from typing import Literal

from pydantic import BaseModel

Role = Literal["student", "guardian", "teacher"]


class ProfileCreate(BaseModel):
    """Fields collected right after Supabase Auth sign-up completes."""

    role: Role
    display_name: str
    grade_level: int | None = None


class Profile(BaseModel):
    """A student, guardian, or teacher profile linked to a Supabase Auth user."""

    id: str
    role: Role
    display_name: str
    grade_level: int | None = None
