"""
FastAPI application entrypoint: creates the app, wires middleware, and
mounts routers. Domain routes are added here as each module's API surface
is implemented.
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import get_settings

settings = get_settings()

app = FastAPI(title="CurriculumMind API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
async def health() -> dict[str, str]:
    """Liveness check used by the hosting platform and local development."""
    return {"status": "ok", "environment": settings.environment}
