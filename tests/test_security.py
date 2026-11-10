from fastapi.testclient import TestClient

from app.db import get_engine
from app.main import app
from app.models import init_db

client = TestClient(app)


def setup_database():
    init_db(get_engine())


def test_management_routes_require_api_key_when_configured(monkeypatch):
    setup_database()
    monkeypatch.setenv("APP_ENV", "production")
    monkeypatch.setenv("APP_API_KEY", "unit-test-value")

    response = client.get("/api/tokens/")
    assert response.status_code == 401

    response = client.get("/api/tokens/", headers={"X-API-Key": "unit-test-value"})
    assert response.status_code == 200


def test_management_routes_fail_closed_when_production_key_missing(monkeypatch):
    setup_database()
    monkeypatch.setenv("APP_ENV", "production")
    monkeypatch.delenv("APP_API_KEY", raising=False)

    response = client.get("/api/tokens/")
    assert response.status_code == 503


def test_development_mode_keeps_local_workflow_compatible(monkeypatch):
    setup_database()
    monkeypatch.setenv("APP_ENV", "development")
    monkeypatch.delenv("APP_API_KEY", raising=False)

    response = client.get("/api/tokens/")
    assert response.status_code == 200
