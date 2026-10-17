import os
import sqlite3

DB_PATH = os.getenv("DB_PATH", "data/prices.db")

NEW_COLUMNS = (
    ("sources_ok", "INTEGER NOT NULL DEFAULT 1"),
    ("confidence", "TEXT NOT NULL DEFAULT 'low'"),
    ("groups_ok", "INTEGER NOT NULL DEFAULT 1"),
    ("estimated", "INTEGER NOT NULL DEFAULT 0"),
)


def get_conn():
    os.makedirs(os.path.dirname(DB_PATH) or ".", exist_ok=True)
    conn = sqlite3.connect(DB_PATH, timeout=10.0)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA synchronous=NORMAL")
    return conn


def init_db():
    with get_conn() as c:
        c.execute("""
            CREATE TABLE IF NOT EXISTS prices (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                asset TEXT NOT NULL,
                price REAL NOT NULL,
                created_at TEXT NOT NULL DEFAULT (datetime('now'))
            )
        """)
        cols = {r["name"] for r in c.execute("PRAGMA table_info(prices)")}
        for name, ddl in NEW_COLUMNS:
            if name not in cols:
                c.execute(f"ALTER TABLE prices ADD COLUMN {name} {ddl}")
        c.execute(
            "CREATE INDEX IF NOT EXISTS idx_prices_asset_id ON prices (asset, id DESC)"
        )
