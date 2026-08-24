"""FastAPI dependency for verifying a Supabase-issued access token."""

from functools import lru_cache

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from supabase import Client, create_client

from app.config import get_settings

_security = HTTPBearer()


@lru_cache
def _get_supabase_client() -> Client:
    """Return a cached Supabase client used only to verify user tokens."""
    settings = get_settings()
    return create_client(settings.supabase_url, settings.supabase_anon_key)


async def get_current_user_id(
    credentials: HTTPAuthorizationCredentials = Depends(_security),
) -> str:
    """Verify the bearer token against Supabase Auth and return the user id."""
    try:
        response = _get_supabase_client().auth.get_user(credentials.credentials)
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="invalid or expired token"
        ) from exc
    if response.user is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="invalid or expired token")
    return response.user.id
