import json
import os
import random
import statistics
import urllib.request
from concurrent.futures import ThreadPoolExecutor

TIMEOUT = float(os.getenv("SOURCE_TIMEOUT", "5"))


class Source:
    name = "base"

    def fetch(self, asset: str) -> float:
        """Return the price or raise an exception."""
        raise NotImplementedError


class FakeSource(Source):
    name = "fake"
    BASE = {"usd": 60000, "gold": 3000000}  # fake numbers

    def fetch(self, asset: str) -> float:
        return self.BASE[asset] * random.uniform(0.98, 1.02)


class HttpJsonSource(Source):
    """Generic source: GET a URL, dig a number out of the JSON.

    config = {"usd": ("https://example.com/api", ["data", "price"])}
    """

    def __init__(self, name: str, config: dict, scale: float = 1.0):
        self.name = name
        self.config = config
        self.scale = scale

    def fetch(self, asset: str) -> float:
        url, path = self.config[asset]
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=TIMEOUT) as resp:
            data = json.load(resp)
        for key in path:
            data = data[key]
        return float(str(data).replace(",", "")) * self.scale


def confidence_for(ok: int) -> str:
    if ok >= 3:
        return "high"
    if ok == 2:
        return "medium"
    return "low"


def collect(asset: str, sources: list):
    """Ask every source in parallel; return the median or None if all fail."""

    def one(source):
        try:
            return float(source.fetch(asset))
        except Exception:
            return None

    if not sources:
        return None
    with ThreadPoolExecutor(max_workers=len(sources)) as pool:
        results = list(pool.map(one, sources))
    prices = [p for p in results if p is not None]
    if not prices:
        return None
    return {
        "price": round(statistics.median(prices)),
        "sources_ok": len(prices),
        "sources_total": len(sources),
        "confidence": confidence_for(len(prices)),
    }


def gold18_gram(ounce_usd: float, usd_price: float) -> float:
    """Estimate 18k gold per gram from the world ounce price and the USD price.
    It is an estimate: it has no local market premium."""
    return ounce_usd / 31.1035 * 0.75 * usd_price
