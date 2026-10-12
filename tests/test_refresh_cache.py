from fastapi.testclient import TestClient

from app import main


def test_refresh_is_cached(monkeypatch):
    monkeypatch.setattr(main, "REFRESH_MIN_INTERVAL", 60)
    with TestClient(main.app) as client:
        client.post("/prices/usd/refresh")
        second = client.post("/prices/usd/refresh").json()
        assert second["cached"] is True
        assert "age_seconds" in second
        assert second["price"] > 0


def test_unknown_asset_is_404_even_with_cache(monkeypatch):
    monkeypatch.setattr(main, "REFRESH_MIN_INTERVAL", 60)
    with TestClient(main.app) as client:
        assert client.post("/prices/xyz/refresh").status_code == 404
