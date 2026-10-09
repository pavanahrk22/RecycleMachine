from fastapi.testclient import TestClient
from app.main import app
from app.config import settings

client = TestClient(app)

def test_api_me_requires_auth():
    response = client.get("/api/me")
    assert response.status_code == 401
    assert "Missing authentication" in response.json()["detail"]

def test_health_does_not_require_auth():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"

def test_dev_auth_bypass_in_dev_mode():
    original_env = settings.ENV
    settings.ENV = "dev"
    try:
        response = client.get("/api/me", headers={"X-Dev-User": "test_student"})
        assert response.status_code == 200
        data = response.json()
        assert data["uid"] == "test_student"
        assert data["pointsBalance"] == 0
        assert data["email"] == "test_student@campus.edu"
    finally:
        settings.ENV = original_env

def test_dev_auth_bypass_fails_in_production():
    original_env = settings.ENV
    settings.ENV = "production"
    settings.ENVIRONMENT = "production"
    try:
        response = client.get("/api/me", headers={"X-Dev-User": "hacker_trying_bypass"})
        # Must strictly fail with 401 in production
        assert response.status_code == 401
        assert "Authorization header" in response.json()["detail"]
    finally:
        settings.ENV = original_env
        settings.ENVIRONMENT = "dev"
