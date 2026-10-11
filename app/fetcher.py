import os

from app.sources import FakeSource, HttpJsonSource, collect, gold18_gram

SUPPORTED = ("usd", "gold")

# USDT price in Iran is used as a proxy for the dollar. Nobitex returns rials.
USD_SOURCES = [
    HttpJsonSource(
        name="nobitex-usdt",
        config={
            "usd": (
                "https://apiv2.nobitex.ir/market/stats?srcCurrency=usdt&dstCurrency=rls",
                ["stats", "usdt-rls", "latest"],
            )
        },
        scale=0.1,  # rial -> toman
        user_agent="TraderBot/PriceTracker-1.0",
    ),
]

# World gold ounce in USD. Both seem to share one upstream, so one group.
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


def _gold_estimate():
    usd = collect("usd", USD_SOURCES)
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
    if os.getenv("USE_FAKE_SOURCES") == "1":  # tests must not hit the network
        result = collect(asset, [FakeSource()])
    elif asset == "usd":
        result = collect("usd", USD_SOURCES)
    else:
        result = _gold_estimate()
    if result is None:
        raise RuntimeError("no source available")
    return result
