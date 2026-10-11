import os
os.environ["DB_PATH"] = "/tmp/test_prices.db"
os.environ["USE_FAKE_SOURCES"] = "1"

from fastapi.testclient import TestClient
from app.main import app

def test_health():
    with TestClient(app) as client:
        assert client.get("/health").json() == {"status": "ok"}

def test_refresh_and_history():
    with TestClient(app) as client:
        r = client.post("/prices/usd/refresh")
        assert r.status_code == 200
        assert len(client.get("/prices/usd/history").json()) >= 1

def test_unknown_asset():
    with TestClient(app) as client:
        assert client.post("/prices/xyz/refresh").status_code == 404


def test_latest_has_age_and_confidence():
    with TestClient(app) as client:
        client.post("/prices/usd/refresh")
        data = client.get("/prices/usd/latest").json()
        assert "age_seconds" in data
        assert data["stale"] is False
        assert data["confidence"] in ("low", "medium", "high")
