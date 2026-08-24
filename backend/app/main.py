"""
FastAPI application entrypoint: creates the app, wires middleware, and
mounts routers. Domain routes are added here as each module's API surface
is implemented.
"""

from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.config import get_settings
from app.db import get_pool
from app.identity.router import router as identity_router
from app.tutoring.router import router as tutoring_router

settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Open the shared database pool for the app's lifetime, close it on shutdown."""
    pool = get_pool()
    await pool.open()
    yield
    await pool.close()


app = FastAPI(title="CurriculumMind API", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["X-Conversation-Id"],
)

app.include_router(identity_router)
app.include_router(tutoring_router)


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """
    Ensure unexpected errors still get a normal CORS-safe JSON response.

    An exception that reaches Starlette's outermost error handler sits
    outside the CORS middleware, so the resulting 500 has no CORS headers
    -- the browser then blocks it entirely and the frontend sees "Failed
    to fetch" instead of a visible 500. Handling exceptions inside the
    app (below CORS middleware in the stack) avoids that.
    """
    return JSONResponse(status_code=500, content={"detail": "internal server error"})


@app.get("/health")
async def health() -> dict[str, str]:
    """Liveness check used by the hosting platform and local development."""
    return {"status": "ok", "environment": settings.environment}
