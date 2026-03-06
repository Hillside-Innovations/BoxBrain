"""SQLite database: box records and metadata. Local-only."""
import aiosqlite
from pathlib import Path

from config import settings


DB_PATH = settings.db_path
SCHEMA = """
CREATE TABLE IF NOT EXISTS boxes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    label TEXT NOT NULL UNIQUE,
    location TEXT,
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at TEXT NOT NULL DEFAULT (datetime('now')),
    video_filename TEXT
);
"""


async def get_db() -> aiosqlite.Connection:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = await aiosqlite.connect(str(DB_PATH))
    conn.row_factory = aiosqlite.Row
    return conn


async def init_db() -> None:
    conn = await get_db()
    try:
        await conn.execute(SCHEMA)
        await conn.commit()
    finally:
        await conn.close()
