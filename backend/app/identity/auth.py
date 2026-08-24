"""FastAPI dependency for verifying a Supabase-issued access token."""

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from supabase import create_client

from app.config import get_settings

_security = HTTPBearer()


async def get_current_user_id(
    credentials: HTTPAuthorizationCredentials = Depends(_security),
) -> str:
    """Verify the bearer token against Supabase Auth and return the user id."""
    # A fresh client per call, deliberately not cached/shared: supabase-py's
    # auth module carries session-like internal state, and a shared client
    # verifying back-to-back requests produced an intermittent "invalid or
    # expired token" failure on the second call in testing.
    settings = get_settings()
    client = create_client(settings.supabase_url, settings.supabase_anon_key)
    try:
        response = client.auth.get_user(credentials.credentials)
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="invalid or expired token"
        ) from exc
    if response.user is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="invalid or expired token")
    return response.user.id
