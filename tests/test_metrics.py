import os

os.environ["DB_PATH"] = "/tmp/test_prices.db"
os.environ["USE_FAKE_SOURCES"] = "1"
os.environ["DISABLE_POLLER"] = "1"

import socket
import urllib.error

from fastapi.testclient import TestClient

from app import sources
from app.main import app
from app.sources import Source, classify_error, collect


class Ok(Source):
    def __init__(self, name, price):
        self.name = name
        self.price = price

    def fetch(self, asset):
        return self.price


class Boom(Source):
    name = "boom"

    def __init__(self, exc):
        self.exc = exc

    def fetch(self, asset):
        raise self.exc


def test_classify_errors():
    assert classify_error(urllib.error.URLError(socket.gaierror(-2, "no name"))) == "dns"
    assert classify_error(urllib.error.URLError(TimeoutError())) == "timeout"
    assert classify_error(TimeoutError()) == "timeout"
    assert classify_error(urllib.error.HTTPError("http://x", 403, "Forbidden", None, None)) == "http_error"
    assert classify_error(KeyError("price")) == "bad_response"
    assert classify_error(ConnectionResetError()) == "connection"


def test_failure_and_success_are_recorded():
    sources.reset_stats()
    collect("usd", [Boom(TimeoutError()), Ok("a", 100)])
    snap = sources.snapshot()
    assert snap["boom"]["up"] is False
    assert snap["boom"]["failures"] == {"timeout": 1}
    assert snap["a"]["up"] is True
    assert snap["a"]["last_success_ts"] is not None


def test_metrics_endpoint():
    with TestClient(app) as client:
        client.post("/prices/usd/refresh")
        text = client.get("/metrics").text
        assert 'price_tracker_source_up{source="fake"} 1.0' in text
        assert 'price_tracker_price{asset="usd"}' in text
        assert "price_tracker_source_requests_total" in text


def test_sources_endpoint():
    with TestClient(app) as client:
        client.post("/prices/usd/refresh")
        data = client.get("/sources").json()
        assert data["fake"]["up"] is True
        assert "last_success_age_seconds" in data["fake"]
