from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException
from app import db, fetcher

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
        price = fetcher.fetch_price(asset)
    except ValueError:
        raise HTTPException(status_code=404, detail="unknown asset")
    with db.get_conn() as c:
        c.execute("INSERT INTO prices (asset, price) VALUES (?, ?)", (asset, price))
    return {"asset": asset, "price": price}

@app.get("/prices/{asset}/history")
def history(asset: str, limit: int = 50):
    with db.get_conn() as c:
        rows = c.execute(
            "SELECT price, created_at FROM prices WHERE asset=? ORDER BY id DESC LIMIT ?",
            (asset, limit),
        ).fetchall()
    return [dict(r) for r in rows]
