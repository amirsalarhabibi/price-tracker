import asyncio
import logging
import os
import time
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Response
from prometheus_client import CONTENT_TYPE_LATEST, generate_latest

from app import db, fetcher, metrics, sources

logging.basicConfig(level=logging.INFO)
log = logging.getLogger("price-tracker")

STALE_AFTER = 900  # seconds
POLL_INTERVAL = int(os.getenv("POLL_INTERVAL", "60"))
# POST /refresh returns the stored price when it is younger than this (seconds).
REFRESH_MIN_INTERVAL = int(os.getenv("REFRESH_MIN_INTERVAL", "10"))


def refresh_asset(asset: str) -> dict:
    """Fetch one asset and store it. Raises ValueError or RuntimeError."""
    r = fetcher.fetch_price(asset)
    with db.get_conn() as c:
        c.execute(
            "INSERT INTO prices (asset, price, sources_ok, groups_ok, confidence, estimated) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            (asset, r["price"], r["sources_ok"], r["groups_ok"],
             r["confidence"], int(r.get("estimated", False))),
        )
    return r


def _latest_row(asset: str):
    with db.get_conn() as c:
        return c.execute(
            "SELECT price, sources_ok, groups_ok, confidence, estimated, "
            "CAST(strftime('%s','now') - strftime('%s', created_at) AS INTEGER) AS age_seconds "
            "FROM prices WHERE asset=? ORDER BY id DESC LIMIT 1",
            (asset,),
        ).fetchone()


async def poll_forever():
    while True:
        for asset in fetcher.SUPPORTED:
            try:
                r = await asyncio.to_thread(refresh_asset, asset)
                log.info("poll %s ok: %s (%s)", asset, r["price"], r["confidence"])
            except Exception as e:  # one failure must not stop the loop
                log.warning("poll %s failed: %s", asset, e)
        await asyncio.sleep(POLL_INTERVAL)


@asynccontextmanager
async def lifespan(app: FastAPI):
    db.init_db()
    task = None
    if os.getenv("DISABLE_POLLER") != "1":
        task = asyncio.create_task(poll_forever())
    yield
    if task:
        task.cancel()


app = FastAPI(title="Price Tracker", lifespan=lifespan)


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/prices/{asset}/refresh")
def refresh(asset: str):
    if asset not in fetcher.SUPPORTED:
        raise HTTPException(status_code=404, detail="unknown asset")
    row = _latest_row(asset)
    if row is not None and row["age_seconds"] < REFRESH_MIN_INTERVAL:
        return {
            "asset": asset,
            "price": row["price"],
            "sources_ok": row["sources_ok"],
            "groups_ok": row["groups_ok"],
            "confidence": row["confidence"],
            "estimated": bool(row["estimated"]),
            "cached": True,
            "age_seconds": row["age_seconds"],
        }
    try:
        r = refresh_asset(asset)
    except ValueError:
        raise HTTPException(status_code=404, detail="unknown asset")
    except RuntimeError:
        raise HTTPException(status_code=503, detail="no source available")
    return {"asset": asset, **r, "cached": False}


@app.get("/prices/{asset}/latest")
def latest(asset: str):
    with db.get_conn() as c:
        row = c.execute(
            "SELECT price, sources_ok, groups_ok, confidence, estimated, created_at, "
            "CAST(strftime('%s','now') - strftime('%s', created_at) AS INTEGER) AS age_seconds "
            "FROM prices WHERE asset=? ORDER BY id DESC LIMIT 1",
            (asset,),
        ).fetchone()
    if row is None:
        raise HTTPException(status_code=404, detail="no data yet")
    data = dict(row)
    data["estimated"] = bool(data["estimated"])
    data["stale"] = data["age_seconds"] > STALE_AFTER
    return data


@app.get("/prices/{asset}/history")
def history(asset: str, limit: int = 50):
    with db.get_conn() as c:
        rows = c.execute(
            "SELECT price, sources_ok, groups_ok, confidence, estimated, created_at "
            "FROM prices WHERE asset=? ORDER BY id DESC LIMIT ?",
            (asset, limit),
        ).fetchall()
    return [{**dict(r), "estimated": bool(r["estimated"])} for r in rows]


@app.get("/sources")
def sources_status():
    now = time.time()
    out = {}
    for name, s in sources.snapshot().items():
        ts = s["last_success_ts"]
        out[name] = {**s, "last_success_age_seconds": None if ts is None else int(now - ts)}
    return out


@app.get("/metrics")
def metrics_endpoint():
    return Response(generate_latest(metrics.REGISTRY), media_type=CONTENT_TYPE_LATEST)
