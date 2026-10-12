from app import fetcher
from app.sources import Source


def test_gold_reuses_the_usd_result(monkeypatch):
    calls = []

    class Counting(Source):
        name = "counting"

        def fetch(self, asset):
            calls.append(asset)
            return 100.0

    monkeypatch.delenv("USE_FAKE_SOURCES", raising=False)
    monkeypatch.setattr(fetcher, "USD_SOURCES", [Counting()])
    monkeypatch.setattr(fetcher, "OUNCE_SOURCES", [Counting()])
    fetcher._usd_cache.update(ts=0.0, value=None)

    fetcher.fetch_price("usd")
    fetcher.fetch_price("gold")

    assert calls.count("usd") == 1
