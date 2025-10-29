import sqlite3
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path
from typing import Iterable, List, Optional, Tuple


SCHEMA_SQL = """
PRAGMA journal_mode=WAL;
CREATE TABLE IF NOT EXISTS posts (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  product_id TEXT NOT NULL,
  posted_at TIMESTAMP NOT NULL,
  price numeric,
  coupon TEXT,
  UNIQUE(product_id, posted_at)
);

CREATE INDEX IF NOT EXISTS idx_posts_product_time ON posts(product_id, posted_at);

CREATE TABLE IF NOT EXISTS counters (
  key TEXT PRIMARY KEY,
  value INTEGER NOT NULL
);

CREATE TABLE IF NOT EXISTS state (
  key TEXT PRIMARY KEY,
  value TEXT NOT NULL
);

-- simple click metrics placeholder
CREATE TABLE IF NOT EXISTS clicks (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  product_id TEXT NOT NULL,
  clicked_at TIMESTAMP NOT NULL
);
"""


class Database:
    def __init__(self, path: str) -> None:
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(path, check_same_thread=False)
        self._conn.execute("PRAGMA foreign_keys = ON;")
        self._conn.executescript(SCHEMA_SQL)
        self._conn.commit()

    def close(self) -> None:
        self._conn.close()

    # Posts
    def record_post(self, product_id: str, posted_at: datetime, price: float, coupon: Optional[str]) -> None:
        self._conn.execute(
            "INSERT OR IGNORE INTO posts(product_id, posted_at, price, coupon) VALUES (?, ?, ?, ?)",
            (product_id, posted_at.isoformat(), price, coupon or None),
        )
        self._conn.commit()

    def posted_within(self, product_id: str, since: datetime) -> bool:
        cur = self._conn.execute(
            "SELECT 1 FROM posts WHERE product_id=? AND posted_at>=? LIMIT 1",
            (product_id, since.isoformat()),
        )
        return cur.fetchone() is not None

    def get_recent_posts(self, limit: int = 10) -> List[Tuple[str, str, Optional[float]]]:
        cur = self._conn.execute(
            "SELECT product_id, posted_at, price FROM posts ORDER BY posted_at DESC LIMIT ?",
            (limit,),
        )
        return list(cur.fetchall())

    # Counters
    def get_counter(self, key: str) -> int:
        cur = self._conn.execute("SELECT value FROM counters WHERE key=?", (key,))
        row = cur.fetchone()
        return int(row[0]) if row else 0

    def set_counter(self, key: str, value: int) -> None:
        self._conn.execute(
            "INSERT INTO counters(key, value) VALUES(?, ?) ON CONFLICT(key) DO UPDATE SET value=excluded.value",
            (key, value),
        )
        self._conn.commit()

    # State
    def get_state(self, key: str, default: Optional[str] = None) -> Optional[str]:
        cur = self._conn.execute("SELECT value FROM state WHERE key=?", (key,))
        row = cur.fetchone()
        return row[0] if row else default

    def set_state(self, key: str, value: str) -> None:
        self._conn.execute(
            "INSERT INTO state(key, value) VALUES(?, ?) ON CONFLICT(key) DO UPDATE SET value=excluded.value",
            (key, value),
        )
        self._conn.commit()

    # Click metrics (placeholder)
    def record_click(self, product_id: str, ts: datetime) -> None:
        self._conn.execute(
            "INSERT INTO clicks(product_id, clicked_at) VALUES (?, ?)",
            (product_id, ts.isoformat()),
        )
        self._conn.commit()


