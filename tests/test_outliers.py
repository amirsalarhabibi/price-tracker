from fastapi.testclient import TestClient

from app import sources
from app.main import app
from app.sources import Source, collect


class Ok(Source):
    def __init__(self, name, price):
        self.name = name
        self.price = price

    def fetch(self, asset):
        return self.price


def test_far_group_is_dropped_as_outlier():
    sources.reset_stats()
    r = collect("usd", [Ok("a", 100), Ok("b", 101), Ok("c", 500)])
    assert r["outliers"] == 1
    assert r["groups_ok"] == 2
    assert r["price"] == 100.5
    assert r["confidence"] == "medium"
    assert sources.snapshot()["c"]["outliers"] == 1


def test_close_groups_are_not_outliers():
    sources.reset_stats()
    r = collect("usd", [Ok("a", 100), Ok("b", 101), Ok("c", 102)])
    assert r["outliers"] == 0
    assert r["confidence"] == "high"


def test_two_sources_that_disagree_get_low_confidence():
    sources.reset_stats()
    r = collect("usd", [Ok("a", 100), Ok("b", 200)])
    assert r["groups_ok"] == 2
    assert r["confidence"] == "low"


def test_outlier_metric_and_circuit_gauge_are_exposed():
    sources.reset_stats()
    collect("usd", [Ok("a", 100), Ok("b", 101), Ok("c", 500)])
    with TestClient(app) as client:
        text = client.get("/metrics").text
    assert 'price_tracker_source_outliers_total{source="c"} 1.0' in text
    assert 'price_tracker_source_circuit_open{source="a"} 0.0' in text
