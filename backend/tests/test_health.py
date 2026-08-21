"""Smoke test confirming the FastAPI app boots and responds."""

from fastapi.testclient import TestClient

from app.main import app


def test_health_ok() -> None:
    """The /health endpoint returns 200 with a status field."""
    client = TestClient(app)
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"
