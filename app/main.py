import asyncio
import logging
import os
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException

from app import db, fetcher

logging.basicConfig(level=logging.INFO)
log = logging.getLogger("price-tracker")

STALE_AFTER = 900  # seconds
POLL_INTERVAL = int(os.getenv("POLL_INTERVAL", "60"))


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
    try:
        r = refresh_asset(asset)
    except ValueError:
        raise HTTPException(status_code=404, detail="unknown asset")
    except RuntimeError:
        raise HTTPException(status_code=503, detail="no source available")
    return {"asset": asset, **r}


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
