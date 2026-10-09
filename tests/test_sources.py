from app.sources import Source, collect, gold18_gram


class Ok(Source):
    def __init__(self, name, price):
        self.name = name
        self.price = price

    def fetch(self, asset):
        return self.price


class Bad(Source):
    name = "bad"

    def fetch(self, asset):
        raise TimeoutError("down")


def test_median_ignores_outlier():
    r = collect("usd", [Ok("a", 100), Ok("b", 102), Ok("c", 500)])
    assert r["price"] == 102
    assert r["confidence"] == "high"


def test_failed_source_is_skipped():
    r = collect("usd", [Ok("a", 100), Bad()])
    assert r["sources_ok"] == 1
    assert r["sources_total"] == 2
    assert r["confidence"] == "low"


def test_two_sources_medium():
    r = collect("usd", [Ok("a", 100), Ok("b", 110), Bad()])
    assert r["price"] == 105
    assert r["confidence"] == "medium"


def test_all_fail_returns_none():
    assert collect("usd", [Bad(), Bad()]) is None


def test_gold18_formula():
    assert round(gold18_gram(31.1035, 100000)) == 75000
