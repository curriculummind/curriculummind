"""
FastAPI application entrypoint: creates the app, wires middleware, and
mounts routers. Domain routes are added here as each module's API surface
is implemented.
"""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.types import ASGIApp

from app.config import get_settings
from app.db import get_pool
from app.identity.router import router as identity_router
from app.tutoring.router import router as tutoring_router

logger = logging.getLogger("curriculummind")
settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Open the shared database pool for the app's lifetime, close it on shutdown."""
    pool = get_pool()
    await pool.open()
    yield
    await pool.close()


app = FastAPI(title="CurriculumMind API", lifespan=lifespan)


@app.middleware("http")
async def catch_unhandled_exceptions(request: Request, call_next: ASGIApp) -> JSONResponse:
    """
    Ensure unexpected errors still produce a normal CORS-safe response.

    @app.exception_handler(Exception) does NOT work for this: FastAPI
    routes any handler registered for the bare Exception class to
    ServerErrorMiddleware, which sits outside CORSMiddleware in the
    stack regardless of registration order, so CORS headers never reach
    a response built that way -- the browser blocks it entirely and the
    frontend sees "Failed to fetch" instead of a visible 500. This is
    registered *before* CORSMiddleware below (Starlette's add_middleware
    inserts at the front, so the later registration ends up outer),
    which puts CORS in a position to add headers to whatever this
    returns, including on an unhandled exception.
    """
    try:
        return await call_next(request)
    except Exception:
        logger.exception("Unhandled exception in %s %s", request.method, request.url.path)
        return JSONResponse(status_code=500, content={"detail": "internal server error"})


app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["X-Conversation-Id", "X-Tutoring-Phase"],
)

app.include_router(identity_router)
app.include_router(tutoring_router)


@app.get("/health")
async def health() -> dict[str, str]:
    """Liveness check used by the hosting platform and local development."""
    return {"status": "ok", "environment": settings.environment}
