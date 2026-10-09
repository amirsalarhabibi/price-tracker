from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException
from app import db, fetcher

STALE_AFTER = 900  # seconds


@asynccontextmanager
async def lifespan(app: FastAPI):
    db.init_db()
    yield


app = FastAPI(title="Price Tracker", lifespan=lifespan)


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/prices/{asset}/refresh")
def refresh(asset: str):
    try:
        r = fetcher.fetch_price(asset)
    except ValueError:
        raise HTTPException(status_code=404, detail="unknown asset")
    except RuntimeError:
        raise HTTPException(status_code=503, detail="no source available")
    with db.get_conn() as c:
        c.execute(
            "INSERT INTO prices (asset, price, sources_ok, confidence) VALUES (?, ?, ?, ?)",
            (asset, r["price"], r["sources_ok"], r["confidence"]),
        )
    return {"asset": asset, **r}


@app.get("/prices/{asset}/latest")
def latest(asset: str):
    with db.get_conn() as c:
        row = c.execute(
            "SELECT price, sources_ok, confidence, created_at, "
            "CAST(strftime('%s','now') - strftime('%s', created_at) AS INTEGER) AS age_seconds "
            "FROM prices WHERE asset=? ORDER BY id DESC LIMIT 1",
            (asset,),
        ).fetchone()
    if row is None:
        raise HTTPException(status_code=404, detail="no data yet")
    data = dict(row)
    data["stale"] = data["age_seconds"] > STALE_AFTER
    return data


@app.get("/prices/{asset}/history")
def history(asset: str, limit: int = 50):
    with db.get_conn() as c:
        rows = c.execute(
            "SELECT price, sources_ok, confidence, created_at "
            "FROM prices WHERE asset=? ORDER BY id DESC LIMIT ?",
            (asset, limit),
        ).fetchall()
    return [dict(r) for r in rows]
