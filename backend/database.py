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

SCHEMA_LOCATIONS = """
CREATE TABLE IF NOT EXISTS locations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL UNIQUE COLLATE NOCASE,
    color TEXT NOT NULL DEFAULT '#5dd9f7',
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);
"""


async def get_db() -> aiosqlite.Connection:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = await aiosqlite.connect(str(DB_PATH))
    await conn.execute("PRAGMA foreign_keys = ON")
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


async def _ensure_location_id_column(conn: aiosqlite.Connection) -> None:
    cursor = await conn.execute("PRAGMA table_info(boxes)")
    rows = await cursor.fetchall()
    names = [row[1] for row in rows]
    if "location_id" not in names:
        await conn.execute(
            "ALTER TABLE boxes ADD COLUMN location_id INTEGER REFERENCES locations(id) ON DELETE SET NULL"
        )
        await conn.commit()


async def _migrate_legacy_box_locations(conn: aiosqlite.Connection) -> None:
    """Link saved locations from legacy boxes.location text (idempotent)."""
    cursor = await conn.execute(
        """
        SELECT DISTINCT TRIM(location) AS loc FROM boxes
        WHERE location IS NOT NULL AND TRIM(location) != ''
        """
    )
    for row in await cursor.fetchall():
        name = row[0]
        await conn.execute(
            "INSERT OR IGNORE INTO locations (name, color) VALUES (?, ?)",
            (name, "#94a3b8"),
        )
    await conn.commit()
    await conn.execute(
        """
        UPDATE boxes SET location_id = (
            SELECT l.id FROM locations l
            WHERE l.name = TRIM(boxes.location) COLLATE NOCASE
            LIMIT 1
        )
        WHERE location IS NOT NULL AND TRIM(location) != '' AND location_id IS NULL
        """
    )
    await conn.commit()


async def init_db() -> None:
    conn = await get_db()
    try:
        await conn.execute(SCHEMA_BOXES)
        await conn.execute(SCHEMA_LOCATIONS)
        await conn.execute(SCHEMA_BOX_CONTENTS)
        await conn.execute(SCHEMA_INDEX)
        await conn.commit()
        await _ensure_diagnostics_columns(conn)
        await _ensure_location_id_column(conn)
        await _migrate_legacy_box_locations(conn)
    finally:
        await conn.close()
