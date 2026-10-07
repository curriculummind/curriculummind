"""Data shapes for student and guardian profiles."""

from typing import Literal

from pydantic import BaseModel, model_validator

Role = Literal["student", "guardian", "teacher"]


class ProfileCreate(BaseModel):
    """
    Fields collected right after Supabase Auth sign-up completes.

    class_code is how a student links to a teacher (Decision 024): a
    student must redeem one, a teacher never submits one (their own
    code is generated server-side instead). student_link_code is the
    mirror image for a parent (Decision 034): a guardian must redeem
    their child's code, a student never submits one (theirs is also
    generated server-side).
    """

    role: Role
    display_name: str
    grade_level: int | None = None
    class_code: str | None = None
    student_link_code: str | None = None

    @model_validator(mode="after")
    def _validate_class_code(self) -> "ProfileCreate":
        if self.role == "student":
            if not self.class_code or not self.class_code.strip():
                raise ValueError("class_code is required to sign up as a student")
            self.class_code = self.class_code.strip().upper()
        elif self.class_code is not None:
            raise ValueError(f"class_code cannot be set for role '{self.role}'")
        return self

    @model_validator(mode="after")
    def _validate_student_link_code(self) -> "ProfileCreate":
        if self.role == "guardian":
            if not self.student_link_code or not self.student_link_code.strip():
                raise ValueError("student_link_code is required to sign up as a parent")
            self.student_link_code = self.student_link_code.strip().upper()
        elif self.student_link_code is not None:
            raise ValueError(f"student_link_code cannot be set for role '{self.role}'")
        return self


class Profile(BaseModel):
    """A student, guardian, or teacher profile linked to a Supabase Auth user."""

    id: str
    role: Role
    display_name: str
    grade_level: int | None = None
    class_code: str | None = None
    student_link_code: str | None = None
    subscription_status: str = "free"
