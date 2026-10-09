import os
import sqlite3

DB_PATH = os.getenv("DB_PATH", "data/prices.db")


def get_conn():
    os.makedirs(os.path.dirname(DB_PATH) or ".", exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
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
        if "sources_ok" not in cols:
            c.execute("ALTER TABLE prices ADD COLUMN sources_ok INTEGER NOT NULL DEFAULT 1")
        if "confidence" not in cols:
            c.execute("ALTER TABLE prices ADD COLUMN confidence TEXT NOT NULL DEFAULT 'low'")
