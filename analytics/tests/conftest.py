import pytest
from fastapi.testclient import TestClient

from app.main import app


@pytest.fixture
def client():
    """Plain (non-context-manager) TestClient: routes work without running
    lifespan, which avoids every test depending on a live Postgres/Redis
    connection just to exercise request/response wiring."""
    return TestClient(app)
