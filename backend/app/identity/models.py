"""Data shapes for student and guardian profiles."""

from typing import Literal

from pydantic import BaseModel, model_validator

Role = Literal["student", "guardian", "teacher"]


class ProfileCreate(BaseModel):
    """
    Fields collected right after Supabase Auth sign-up completes.

    class_code is how a student links to a teacher (Decision 024): a
    student must redeem one, a teacher never submits one (their own
    code is generated server-side instead).
    """

    role: Role
    display_name: str
    grade_level: int | None = None
    class_code: str | None = None

    @model_validator(mode="after")
    def _validate_class_code(self) -> "ProfileCreate":
        if self.role == "student":
            if not self.class_code or not self.class_code.strip():
                raise ValueError("class_code is required to sign up as a student")
            self.class_code = self.class_code.strip().upper()
        elif self.class_code is not None:
            raise ValueError(f"class_code cannot be set for role '{self.role}'")
        return self


class Profile(BaseModel):
    """A student, guardian, or teacher profile linked to a Supabase Auth user."""

    id: str
    role: Role
    display_name: str
    grade_level: int | None = None
    class_code: str | None = None
