"""HTTP routes for profile creation and retrieval."""

from fastapi import APIRouter, Depends, HTTPException, status

from app.db import get_pool
from app.identity.auth import get_current_user_id
from app.identity.models import Profile, ProfileCreate
from app.identity.profiles import create_profile, get_profile

router = APIRouter(prefix="/profile", tags=["identity"])


@router.post("", response_model=Profile, status_code=status.HTTP_201_CREATED)
async def create_my_profile(data: ProfileCreate, user_id: str = Depends(get_current_user_id)) -> Profile:
    """Create the profile for the currently authenticated user, once."""
    pool = get_pool()
    if await get_profile(pool, user_id) is not None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="profile already exists")
    return await create_profile(pool, user_id, data)


@router.get("/me", response_model=Profile)
async def read_my_profile(user_id: str = Depends(get_current_user_id)) -> Profile:
    """Return the currently authenticated user's profile."""
    profile = await get_profile(get_pool(), user_id)
    if profile is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="profile not found")
    return profile
