"""SQLite database: box records and metadata. Local-only."""
import aiosqlite
from pathlib import Path

from config import settings


DB_PATH = settings.db_path
SCHEMA_BOXES = """
CREATE TABLE IF NOT EXISTS boxes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    label TEXT NOT NULL UNIQUE,
    location TEXT,
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at TEXT NOT NULL DEFAULT (datetime('now')),
    video_filename TEXT,
    scan_frame_count INTEGER,
    scan_brightness REAL,
    scan_blur_score REAL
);
"""
SCHEMA_BOX_CONTENTS = """
CREATE TABLE IF NOT EXISTS box_contents (
    box_id INTEGER NOT NULL REFERENCES boxes(id) ON DELETE CASCADE,
    item_text TEXT NOT NULL
);
"""
SCHEMA_INDEX = "CREATE INDEX IF NOT EXISTS ix_box_contents_box_id ON box_contents(box_id);"


async def get_db() -> aiosqlite.Connection:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = await aiosqlite.connect(str(DB_PATH))
    conn.row_factory = aiosqlite.Row
    return conn


async def _ensure_diagnostics_columns(conn: aiosqlite.Connection) -> None:
    """Add scan diagnostics columns if missing (existing DBs)."""
    cursor = await conn.execute("PRAGMA table_info(boxes)")
    rows = await cursor.fetchall()
    names = [row[1] for row in rows]
    for col, typ in [("scan_frame_count", "INTEGER"), ("scan_brightness", "REAL"), ("scan_blur_score", "REAL")]:
        if col not in names:
            await conn.execute(f"ALTER TABLE boxes ADD COLUMN {col} {typ}")
            await conn.commit()


async def init_db() -> None:
    conn = await get_db()
    try:
        await conn.execute(SCHEMA_BOXES)
        await conn.execute(SCHEMA_BOX_CONTENTS)
        await conn.execute(SCHEMA_INDEX)
        await conn.commit()
        await _ensure_diagnostics_columns(conn)
    finally:
        await conn.close()
