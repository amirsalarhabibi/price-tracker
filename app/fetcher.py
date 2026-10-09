from app.sources import FakeSource, collect

SUPPORTED = ("usd", "gold")

# Real sources will be added here once we test which ones respond.
SOURCES = [FakeSource()]


def fetch_price(asset: str) -> dict:
    if asset not in SUPPORTED:
        raise ValueError(f"unknown asset: {asset}")
    result = collect(asset, SOURCES)
    if result is None:
        raise RuntimeError("no source available")
    return result
