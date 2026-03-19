import aiosqlite
from fastapi import APIRouter, Depends, HTTPException
from typing import AsyncGenerator

from database import get_db
from models import LocationCreate, LocationResponse, LocationUpdate


router = APIRouter(prefix="/locations", tags=["locations"])


async def db_conn() -> AsyncGenerator[aiosqlite.Connection, None]:
    conn = await get_db()
    try:
        yield conn
    finally:
        await conn.close()


def _row_to_location(r) -> LocationResponse:
    return LocationResponse(id=r[0], name=r[1], color=r[2], created_at=r[3])


@router.get("", response_model=list[LocationResponse])
async def list_locations(conn: aiosqlite.Connection = Depends(db_conn)):
    cursor = await conn.execute(
        "SELECT id, name, color, created_at FROM locations ORDER BY name COLLATE NOCASE"
    )
    rows = await cursor.fetchall()
    return [_row_to_location(r) for r in rows]


@router.post("", response_model=LocationResponse)
async def create_location(body: LocationCreate, conn: aiosqlite.Connection = Depends(db_conn)):
    try:
        cursor = await conn.execute(
            "INSERT INTO locations (name, color) VALUES (?, ?)",
            (body.name.strip(), body.color),
        )
        await conn.commit()
        row = await conn.execute(
            "SELECT id, name, color, created_at FROM locations WHERE id = ?",
            (cursor.lastrowid,),
        )
        r = await row.fetchone()
        return _row_to_location(r)
    except aiosqlite.IntegrityError as e:
        if "UNIQUE" in str(e):
            raise HTTPException(status_code=409, detail="A location with this name already exists")
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/{location_id}", response_model=LocationResponse)
async def get_location(location_id: int, conn: aiosqlite.Connection = Depends(db_conn)):
    cursor = await conn.execute(
        "SELECT id, name, color, created_at FROM locations WHERE id = ?",
        (location_id,),
    )
    r = await cursor.fetchone()
    if not r:
        raise HTTPException(status_code=404, detail="Location not found")
    return _row_to_location(r)


@router.patch("/{location_id}", response_model=LocationResponse)
async def update_location(
    location_id: int,
    body: LocationUpdate,
    conn: aiosqlite.Connection = Depends(db_conn),
):
    data = body.model_dump(exclude_unset=True)
    if not data:
        return await get_location(location_id, conn)

    cursor = await conn.execute(
        "SELECT id, name, color, created_at FROM locations WHERE id = ?",
        (location_id,),
    )
    r = await cursor.fetchone()
    if not r:
        raise HTTPException(status_code=404, detail="Location not found")

    name = data.get("name", r[1])
    if "name" in data:
        name = data["name"].strip()
    color = data.get("color", r[2])

    try:
        await conn.execute(
            "UPDATE locations SET name = ?, color = ? WHERE id = ?",
            (name, color, location_id),
        )
        await conn.commit()
    except aiosqlite.IntegrityError as e:
        if "UNIQUE" in str(e):
            raise HTTPException(status_code=409, detail="A location with this name already exists")
        raise HTTPException(status_code=400, detail=str(e))

    return await get_location(location_id, conn)


@router.delete("/{location_id}", status_code=204)
async def delete_location(location_id: int, conn: aiosqlite.Connection = Depends(db_conn)):
    cursor = await conn.execute("DELETE FROM locations WHERE id = ?", (location_id,))
    await conn.commit()
    if cursor.rowcount == 0:
        raise HTTPException(status_code=404, detail="Location not found")
