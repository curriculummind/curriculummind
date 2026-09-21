"""Data shapes for the guardian-facing roster and notifications feed."""

from datetime import datetime

from pydantic import BaseModel

from app.tutoring.progress import Tier

Category = str


class RosterStudent(BaseModel):
    student_id: str
    display_name: str
    subject_tiers: dict[str, Tier | None]
    needs_attention: bool
    last_active: datetime | None


class RosterResponse(BaseModel):
    students: list[RosterStudent]


class Notification(BaseModel):
    id: str
    student_id: str
    student_display_name: str
    category: Category
    message: str
    created_at: datetime


class NotificationsResponse(BaseModel):
    notifications: list[Notification]
