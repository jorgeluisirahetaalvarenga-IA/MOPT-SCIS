import os
from fastapi.testclient import TestClient
from backend.main import app

os.environ["TESTING"] = "true"

client = TestClient(app)


def test_health_endpoint():
    response = client.get("/health")
    assert response.status_code == 200

    data = response.json()
    assert data["status"] == "healthy"
    assert data["service"] == "scis-api"
