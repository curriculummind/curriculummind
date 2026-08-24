"""
FastAPI application entrypoint: creates the app, wires middleware, and
mounts routers. Domain routes are added here as each module's API surface
is implemented.
"""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

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
)

app.include_router(identity_router)
app.include_router(tutoring_router)


@app.get("/health")
async def health() -> dict[str, str]:
    """Liveness check used by the hosting platform and local development."""
    return {"status": "ok", "environment": settings.environment}
