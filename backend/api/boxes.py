from typing import AsyncGenerator

import aiosqlite
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File

from config import settings
from database import get_db
from models import BoxCreate, BoxUpdate, BoxResponse
from services import VideoProcessor, VisionService, EmbeddingService
from services.vector_store import get_vector_store


router = APIRouter(prefix="/boxes", tags=["boxes"])


async def db_conn() -> AsyncGenerator[aiosqlite.Connection, None]:
    from database import get_db
    conn = await get_db()
    try:
        yield conn
    finally:
        await conn.close()


@router.post("", response_model=BoxResponse)
async def create_box(body: BoxCreate, conn: aiosqlite.Connection = Depends(db_conn)):
    try:
        cursor = await conn.execute(
            "INSERT INTO boxes (label, location) VALUES (?, ?)",
            (body.label, body.location),
        )
        await conn.commit()
        row = await conn.execute(
            "SELECT id, label, location, created_at, updated_at, video_filename FROM boxes WHERE id = ?",
            (cursor.lastrowid,),
        )
        r = await row.fetchone()
        return BoxResponse(
            id=r[0],
            label=r[1],
            location=r[2],
            created_at=r[3],
            updated_at=r[4],
            has_video=bool(r[5]),
        )
    except aiosqlite.IntegrityError as e:
        if "UNIQUE" in str(e):
            raise HTTPException(status_code=409, detail="Box with this label already exists")
        raise HTTPException(status_code=400, detail=str(e))


@router.get("", response_model=list[BoxResponse])
async def list_boxes(conn: aiosqlite.Connection = Depends(db_conn)):
    cursor = await conn.execute(
        "SELECT id, label, location, created_at, updated_at, video_filename FROM boxes ORDER BY id"
    )
    rows = await cursor.fetchall()
    return [
        BoxResponse(
            id=r[0],
            label=r[1],
            location=r[2],
            created_at=r[3],
            updated_at=r[4],
            has_video=bool(r[5]),
        )
        for r in rows
    ]


@router.get("/{box_id}", response_model=BoxResponse)
async def get_box(box_id: int, conn: aiosqlite.Connection = Depends(db_conn)):
    cursor = await conn.execute(
        "SELECT id, label, location, created_at, updated_at, video_filename FROM boxes WHERE id = ?",
        (box_id,),
    )
    r = await cursor.fetchone()
    if not r:
        raise HTTPException(status_code=404, detail="Box not found")
    return BoxResponse(
        id=r[0],
        label=r[1],
        location=r[2],
        created_at=r[3],
        updated_at=r[4],
        has_video=bool(r[5]),
    )


@router.patch("/{box_id}", response_model=BoxResponse)
async def update_box(box_id: int, body: BoxUpdate, conn: aiosqlite.Connection = Depends(db_conn)):
    cursor = await conn.execute(
        "UPDATE boxes SET location = COALESCE(?, location), updated_at = datetime('now') WHERE id = ?",
        (body.location, box_id),
    )
    await conn.commit()
    if cursor.rowcount == 0:
        raise HTTPException(status_code=404, detail="Box not found")
    return await get_box(box_id, conn)


@router.post("/{box_id}/video", response_model=BoxResponse)
async def upload_box_video(
    box_id: int,
    video: UploadFile = File(...),
    conn: aiosqlite.Connection = Depends(db_conn),
):
    if not video.filename or not any(video.filename.lower().endswith(ext) for ext in (".mp4", ".mov", ".webm", ".avi")):
        raise HTTPException(status_code=400, detail="Upload must be a video file (e.g. .mp4, .mov)")
    # Reject oversized uploads (e.g. long phone recordings)
    if video.size is not None and video.size > settings.max_upload_bytes:
        raise HTTPException(
            status_code=413,
            detail=f"Video too large. Max size is {settings.max_upload_bytes // (1024 * 1024)} MB.",
        )
    # Ensure box exists
    cursor = await conn.execute(
        "SELECT id, label FROM boxes WHERE id = ?", (box_id,)
    )
    row = await cursor.fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Box not found")
    box_label = row[1]
    # Save upload
    settings.uploads_dir.mkdir(parents=True, exist_ok=True)
    safe_name = f"{box_id}_{video.filename}"
    video_path = settings.uploads_dir / safe_name
    content = await video.read()
    if len(content) > settings.max_upload_bytes:
        raise HTTPException(
            status_code=413,
            detail=f"Video too large. Max size is {settings.max_upload_bytes // (1024 * 1024)} MB.",
        )
    video_path.write_bytes(content)
    # Extract frames
    vp = VideoProcessor()
    frames = vp.extract_frames(video_path, box_id, max_frames=10)
    if not frames:
        raise HTTPException(status_code=400, detail="Could not extract frames from video")
    # Describe frames (vision)
    vs = VisionService()
    descriptions = vs.describe_frames(frames)
    # Embed and store in ChromaDB
    es = EmbeddingService()
    embeddings = es.embed(descriptions)
    store = get_vector_store()
    store.add(box_id, box_label, descriptions, embeddings)
    # Update box record
    await conn.execute(
        "UPDATE boxes SET video_filename = ?, updated_at = datetime('now') WHERE id = ?",
        (safe_name, box_id),
    )
    await conn.commit()
    return await get_box(box_id, conn)
