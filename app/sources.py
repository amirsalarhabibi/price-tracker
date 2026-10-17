import json
import os
import random
import socket
import ssl
import statistics
import threading
import time
import typing
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor

TIMEOUT = float(os.getenv("SOURCE_TIMEOUT", "5"))
CB_FAIL_THRESHOLD = int(os.getenv("CB_FAIL_THRESHOLD", "3"))
CB_COOLDOWN_SEC = float(os.getenv("CB_COOLDOWN_SEC", "60"))

_lock = threading.Lock()
_stats = {}


def classify_error(exc: Exception) -> str:
    """Name the kind of failure, so a blocked source can be told apart from a broken one."""
    if isinstance(exc, urllib.error.HTTPError):
        return "http_error"
    if isinstance(exc, urllib.error.URLError):
        reason = exc.reason
        if isinstance(reason, socket.gaierror):
            return "dns"
        if isinstance(reason, TimeoutError):
            return "timeout"
        if isinstance(reason, ssl.SSLError):
            return "tls"
        return "connection"
    if isinstance(exc, TimeoutError):
        return "timeout"
    if isinstance(exc, ssl.SSLError):
        return "tls"
    if isinstance(exc, (ValueError, KeyError, TypeError, IndexError)):
        return "bad_response"
    if isinstance(exc, OSError):
        return "connection"
    return "other"


def _entry(source):
    return _stats.setdefault(
        source.name,
        {
            "group": source.group_id(),
            "attempts": 0,
            "failures": {},
            "up": None,
            "last_success_ts": None,
            "last_error": None,
            "consecutive_failures": 0,
            "circuit": "closed",
            "cooldown_until": None,
        },
    )


def is_circuit_open(source) -> bool:
    """Check if the source is temporarily quarantined by the Circuit Breaker."""
    with _lock:
        e = _entry(source)
        if e["circuit"] == "open":
            if e["cooldown_until"] and time.time() >= e["cooldown_until"]:
                e["circuit"] = "half-open"
                return False
            return True
        return False


def record_success(source):
    with _lock:
        e = _entry(source)
        e["attempts"] += 1
        e["up"] = True
        e["last_success_ts"] = time.time()
        e["consecutive_failures"] = 0
        e["circuit"] = "closed"
        e["cooldown_until"] = None


def record_failure(source, exc: Exception):
    kind = classify_error(exc)
    with _lock:
        e = _entry(source)
        e["attempts"] += 1
        e["up"] = False
        e["last_error"] = kind
        e["failures"][kind] = e["failures"].get(kind, 0) + 1
        e["consecutive_failures"] += 1
        if e["consecutive_failures"] >= CB_FAIL_THRESHOLD:
            e["circuit"] = "open"
            e["cooldown_until"] = time.time() + CB_COOLDOWN_SEC


def snapshot() -> dict:
    with _lock:
        return {n: {**e, "failures": dict(e["failures"])} for n, e in _stats.items()}


def reset_stats():
    with _lock:
        _stats.clear()


class Source:
    name = "base"
    group = None  # sources fed by the same upstream share a group

    def group_id(self) -> str:
        return self.group or self.name

    def fetch(self, asset: str) -> float:
        raise NotImplementedError


class FakeSource(Source):
    name = "fake"
    BASE: typing.ClassVar[dict[str, float]] = {"usd": 60000, "gold": 3000000, "xau": 4000}

    def fetch(self, asset: str) -> float:
        return self.BASE[asset] * random.uniform(0.98, 1.02)


class HttpJsonSource(Source):
    def __init__(self, name, config, scale=1.0, group=None, user_agent="Mozilla/5.0"):
        self.name = name
        self.config = config
        self.scale = scale
        self.group = group
        self.user_agent = user_agent

    def fetch(self, asset: str) -> float:
        url, path = self.config[asset]
        req = urllib.request.Request(url, headers={"User-Agent": self.user_agent})
        with urllib.request.urlopen(req, timeout=TIMEOUT) as resp:
            data = json.load(resp)
        for key in path:
            data = data[key]
        val = float(str(data).replace(",", "")) * self.scale
        if val <= 0:
            raise ValueError("non-positive price")
        return val


def confidence_for(groups_ok: int) -> str:
    if groups_ok >= 3:
        return "high"
    if groups_ok == 2:
        return "medium"
    return "low"


def collect(asset: str, sources: list):
    """Ask every source in parallel with Circuit Breaker protection."""

    def one(source):
        if is_circuit_open(source):
            return None
        try:
            price = float(source.fetch(asset))
        except Exception as exc:  # noqa: BLE001
            record_failure(source, exc)
            return None
        record_success(source)
        return price

    if not sources:
        return None
    with ThreadPoolExecutor(max_workers=len(sources)) as pool:
        results = list(pool.map(one, sources))

    by_group = {}
    for source, price in zip(sources, results):
        if price is not None:
            by_group.setdefault(source.group_id(), []).append(price)
    if not by_group:
        return None

    group_prices = [statistics.median(v) for v in by_group.values()]
    return {
        "price": round(statistics.median(group_prices), 2),
        "sources_ok": sum(len(v) for v in by_group.values()),
        "sources_total": len(sources),
        "groups_ok": len(by_group),
        "confidence": confidence_for(len(by_group)),
    }


def gold18_gram(ounce_usd: float, usd_price: float) -> float:
    """Estimate 18k gold per gram from the world ounce price and the USD price.
    It is an estimate: it has no local market premium."""
    return ounce_usd / 31.1035 * 0.75 * usd_price
