import time

from app import sources
from app.sources import Source, collect


class Flaky(Source):
    name = "flaky"

    def __init__(self):
        self.fail = True
        self.calls = 0

    def fetch(self, asset):
        self.calls += 1
        if self.fail:
            raise TimeoutError("down")
        return 100.0


def _setup(monkeypatch):
    monkeypatch.setattr(sources, "CB_FAIL_THRESHOLD", 3)
    monkeypatch.setattr(sources, "CB_COOLDOWN_SEC", 0.3)
    sources.reset_stats()


def test_circuit_opens_after_threshold(monkeypatch):
    _setup(monkeypatch)
    s = Flaky()
    for _ in range(6):
        collect("usd", [s])
    assert s.calls == 3  # the open circuit stopped further calls
    assert sources.snapshot()["flaky"]["circuit"] == "open"


def test_circuit_recovers_after_cooldown(monkeypatch):
    _setup(monkeypatch)
    s = Flaky()
    for _ in range(3):
        collect("usd", [s])
    time.sleep(0.4)
    s.fail = False
    assert collect("usd", [s])["price"] == 100.0
    assert sources.snapshot()["flaky"]["circuit"] == "closed"


def test_failed_trial_reopens_circuit(monkeypatch):
    _setup(monkeypatch)
    s = Flaky()
    for _ in range(3):
        collect("usd", [s])
    time.sleep(0.4)
    before = s.calls
    collect("usd", [s])  # one trial call in the half-open state, it fails
    assert s.calls == before + 1
    assert sources.snapshot()["flaky"]["circuit"] == "open"
    collect("usd", [s])  # blocked again, no new call
    assert s.calls == before + 1
