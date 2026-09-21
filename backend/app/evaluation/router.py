"""HTTP routes for the guardian/teacher dashboard: roster, per-student detail, notifications."""

from fastapi import APIRouter, Depends, HTTPException, status

from app.db import get_pool
from app.evaluation.guardians import build_roster, is_active_guardian_of, list_notifications_for_guardian
from app.evaluation.models import NotificationsResponse, RosterResponse
from app.identity.auth import get_current_user_id
from app.tutoring.progress import MasteryPoint, Module, get_mastery_curve, get_topic_progress

router = APIRouter(prefix="/guardian", tags=["evaluation"])


@router.get("/roster")
async def roster(user_id: str = Depends(get_current_user_id)) -> RosterResponse:
    """Every student linked to the current guardian, with a per-subject tier summary each."""
    pool = get_pool()
    return RosterResponse(students=await build_roster(pool, user_id))


@router.get("/students/{student_id}/progress")
async def student_progress(
    student_id: str, subject: str, grade_band: str = "6", user_id: str = Depends(get_current_user_id)
) -> dict[str, list[Module]]:
    """
    A linked student's per-topic mastery tiers -- same shape and same
    computation as /tutor/progress, just for a student the caller has
    an active guardian_links row for instead of for themselves. 404,
    not 403, on a non-link: never confirm to an unauthorized caller
    whether the id even exists, matching the existing non-owner-
    conversation precedent in tutoring/router.py.
    """
    pool = get_pool()
    if not await is_active_guardian_of(pool, user_id, student_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="student not found")
    modules = await get_topic_progress(pool, student_id, subject_slug=subject, grade_band=grade_band)
    return {"modules": modules}


@router.get("/students/{student_id}/mastery-curve")
async def student_mastery_curve(
    student_id: str, subject: str, grade_band: str = "6", user_id: str = Depends(get_current_user_id)
) -> dict[str, list[MasteryPoint]]:
    """A linked student's mastery curve -- same shape as /tutor/mastery-curve, gated the same way as above."""
    pool = get_pool()
    if not await is_active_guardian_of(pool, user_id, student_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="student not found")
    points = await get_mastery_curve(pool, student_id, subject_slug=subject, grade_band=grade_band)
    return {"points": points}


@router.get("/notifications")
async def notifications(user_id: str = Depends(get_current_user_id)) -> NotificationsResponse:
    """The most recent notifications across every student linked to the current guardian."""
    pool = get_pool()
    return NotificationsResponse(notifications=await list_notifications_for_guardian(pool, user_id))
