import os
import threading
import time

from app.sources import FakeSource, HttpJsonSource, collect, gold18_gram

SUPPORTED = ("usd", "gold")
USD_CACHE_TTL = 20

USD_SOURCES = [
    HttpJsonSource(
        name="nobitex-usdt",
        config={
            "usd": (
                "https://apiv2.nobitex.ir/market/stats?srcCurrency=usdt&dstCurrency=rls",
                ["stats", "usdt-rls", "latest"],
            )
        },
        scale=0.1,
        group="nobitex",
        user_agent="TraderBot/PriceTracker-1.0",
    ),
    HttpJsonSource(
        name="tetherland-usdt",
        config={
            "usd": (
                "https://api.tetherland.com/currencies",
                ["data", "currencies", "USDT", "price"],
            )
        },
        scale=1.0,
        group="tetherland",
        user_agent="TraderBot/PriceTracker-1.0",
    ),
    HttpJsonSource(
        name="wallex-usdt",
        config={
            "usd": (
                "https://api.wallex.ir/v1/markets",
                ["result", "symbols", "USDTTMN", "stats", "lastPrice"],
            )
        },
        scale=1.0,
        group="wallex",
        user_agent="TraderBot/PriceTracker-1.0",
    ),
]

OUNCE_SOURCES = [
    HttpJsonSource(
        "gold-api",
        {"xau": ("https://api.gold-api.com/price/XAU", ["price"])},
        group="gold-api",
    ),
    HttpJsonSource(
        "xaus",
        {"xau": ("https://xaus.com/api/v1/spot", ["spot_usd_oz"])},
        group="gold-api",
    ),
]

_ORDER = {"low": 0, "medium": 1, "high": 2}
_usd_cache = {"ts": 0.0, "value": None}
_usd_lock = threading.Lock()


def _usd_cached():
    with _usd_lock:
        fresh = time.time() - _usd_cache["ts"] < USD_CACHE_TTL
        if _usd_cache["value"] is not None and fresh:
            return _usd_cache["value"]
        value = collect("usd", USD_SOURCES)
        if value is not None:
            _usd_cache.update(ts=time.time(), value=value)
        return value


def _gold_estimate():
    usd = _usd_cached()
    ounce = collect("xau", OUNCE_SOURCES)
    if usd is None or ounce is None:
        return None
    return {
        "price": round(gold18_gram(ounce["price"], usd["price"])),
        "sources_ok": usd["sources_ok"] + ounce["sources_ok"],
        "sources_total": usd["sources_total"] + ounce["sources_total"],
        "groups_ok": min(usd["groups_ok"], ounce["groups_ok"]),
        "confidence": min(usd["confidence"], ounce["confidence"], key=_ORDER.get),
        "estimated": True,
    }


def fetch_price(asset: str) -> dict:
    if asset not in SUPPORTED:
        raise ValueError(f"unknown asset: {asset}")
    if os.getenv("USE_FAKE_SOURCES") == "1":
        result = collect(asset, [FakeSource()])
    elif asset == "usd":
        result = _usd_cached()
    else:
        result = _gold_estimate()
    if result is None:
        raise RuntimeError("no source available")
    return result
