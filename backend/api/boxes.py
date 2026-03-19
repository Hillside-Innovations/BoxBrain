from pathlib import Path
from typing import AsyncGenerator, Dict, List, Optional

import aiosqlite
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from fastapi.responses import FileResponse

from config import settings
from database import get_db
from models import BoxCreate, BoxUpdate, BoxResponse, CaptureDiagnostics
from services import VideoProcessor, VisionService, EmbeddingService
from services.diagnostics import compute_capture_diagnostics
from services.vector_store import get_vector_store


router = APIRouter(prefix="/boxes", tags=["boxes"])

_BOX_SELECT = """
SELECT b.id, b.label, b.location, b.created_at, b.updated_at, b.video_filename,
       b.scan_frame_count, b.scan_brightness, b.scan_blur_score,
       b.location_id, l.name AS loc_name, l.color AS loc_color
FROM boxes b
LEFT JOIN locations l ON l.id = b.location_id
"""


async def db_conn() -> AsyncGenerator[aiosqlite.Connection, None]:
    from database import get_db
    conn = await get_db()
    try:
        yield conn
    finally:
        await conn.close()


def _normalize_caption(text: str) -> str:
    """Lightweight cleanup of vision captions before embedding/search."""
    t = text.strip()
    lower = t.lower()
    prefixes = [
        "this box contains ",
        "this image shows ",
        "a photo of",
        "a picture of",
        "an image of",
        "the image of",
        "a close up of",
    ]
    for p in prefixes:
        if lower.startswith(p):
            t = t[len(p) :].lstrip(" ,.-")
            lower = t.lower()
            break
    return t or text.strip()


@router.post("", response_model=BoxResponse)
async def create_box(body: BoxCreate, conn: aiosqlite.Connection = Depends(db_conn)):
    if body.location_id is not None:
        cur = await conn.execute("SELECT 1 FROM locations WHERE id = ?", (body.location_id,))
        if not await cur.fetchone():
            raise HTTPException(status_code=400, detail="Invalid location_id")
    try:
        cursor = await conn.execute(
            "INSERT INTO boxes (label, location_id) VALUES (?, ?)",
            (body.label, body.location_id),
        )
        await conn.commit()
        row = await conn.execute(f"{_BOX_SELECT} WHERE b.id = ?", (cursor.lastrowid,))
        r = await row.fetchone()
        return _box_response_from_row(r, [])
    except aiosqlite.IntegrityError as e:
        if "UNIQUE" in str(e):
            raise HTTPException(status_code=409, detail="Box with this label already exists")
        raise HTTPException(status_code=400, detail=str(e))


def _box_response_from_row(r, contents: List[str]) -> BoxResponse:
    """Build BoxResponse from a joined boxes+locations row (see _BOX_SELECT column order)."""
    bid = r[0]
    legacy_loc = r[2]
    lid = r[9]
    loc_name = r[10]
    loc_color = r[11]
    if lid and loc_name:
        display_loc = loc_name
        color_out: Optional[str] = loc_color
    elif lid and not loc_name:
        display_loc = legacy_loc
        color_out = None
    else:
        display_loc = legacy_loc if legacy_loc else None
        color_out = None
    return BoxResponse(
        id=bid,
        label=r[1],
        location=display_loc,
        location_id=lid,
        location_color=color_out,
        created_at=r[3],
        updated_at=r[4],
        has_video=bool(r[5]),
        contents=contents,
        diagnostics=_diagnostics_from_row(r, 5),
    )


def _diagnostics_from_row(row: tuple, video_filename_idx: int) -> Optional[CaptureDiagnostics]:
    """Build CaptureDiagnostics from row if scan columns present. Row has ... video_filename, scan_frame_count, scan_brightness, scan_blur_score."""
    if len(row) <= video_filename_idx + 3:
        return None
    fc, bright, blur = row[video_filename_idx + 1], row[video_filename_idx + 2], row[video_filename_idx + 3]
    if fc is None or bright is None or blur is None:
        return None
    return CaptureDiagnostics(frame_count=int(fc), brightness=float(bright), blur_score=float(blur))


async def _contents_for_boxes(conn: aiosqlite.Connection, box_ids: List[int]) -> Dict[int, List[str]]:
    out: Dict[int, List[str]] = {bid: [] for bid in box_ids}
    if not box_ids:
        return out
    placeholders = ",".join("?" * len(box_ids))
    cursor = await conn.execute(
        f"SELECT box_id, item_text FROM box_contents WHERE box_id IN ({placeholders}) ORDER BY box_id",
        box_ids,
    )
    for row in await cursor.fetchall():
        out[row[0]].append(row[1])
    return out


@router.get("", response_model=list[BoxResponse])
async def list_boxes(conn: aiosqlite.Connection = Depends(db_conn)):
    cursor = await conn.execute(f"{_BOX_SELECT} ORDER BY b.id")
    rows = await cursor.fetchall()
    box_ids = [r[0] for r in rows]
    contents_map = await _contents_for_boxes(conn, box_ids)
    return [_box_response_from_row(r, contents_map.get(r[0], [])) for r in rows]


@router.get("/{box_id}", response_model=BoxResponse)
async def get_box(box_id: int, conn: aiosqlite.Connection = Depends(db_conn)):
    cursor = await conn.execute(f"{_BOX_SELECT} WHERE b.id = ?", (box_id,))
    r = await cursor.fetchone()
    if not r:
        raise HTTPException(status_code=404, detail="Box not found")
    contents_map = await _contents_for_boxes(conn, [box_id])
    return _box_response_from_row(r, contents_map.get(box_id, []))


@router.get("/{box_id}/image", response_class=FileResponse)
async def get_box_image(box_id: int):
    """Serve the first frame of the box scan as the box image, or 404 if no scan."""
    frame_dir = settings.frames_dir / str(box_id)
    if not frame_dir.is_dir():
        raise HTTPException(status_code=404, detail="No scan image for this box")
    frames = sorted(frame_dir.glob("frame_*.jpg"))
    if not frames:
        raise HTTPException(status_code=404, detail="No scan image for this box")
    return FileResponse(frames[0], media_type="image/jpeg")


@router.patch("/{box_id}", response_model=BoxResponse)
async def update_box(box_id: int, body: BoxUpdate, conn: aiosqlite.Connection = Depends(db_conn)):
    updates = body.model_dump(exclude_unset=True)
    if updates:
        if "location_id" in updates:
            lid = updates["location_id"]
            if lid is not None:
                cur = await conn.execute("SELECT 1 FROM locations WHERE id = ?", (lid,))
                if not await cur.fetchone():
                    raise HTTPException(status_code=400, detail="Invalid location_id")
            cursor = await conn.execute(
                "UPDATE boxes SET location_id = ?, location = NULL, updated_at = datetime('now') WHERE id = ?",
                (lid, box_id),
            )
            await conn.commit()
            if cursor.rowcount == 0:
                raise HTTPException(status_code=404, detail="Box not found")
    else:
        cur = await conn.execute("SELECT 1 FROM boxes WHERE id = ?", (box_id,))
        if not await cur.fetchone():
            raise HTTPException(status_code=404, detail="Box not found")
    return await get_box(box_id, conn)


@router.delete("/{box_id}", status_code=204)
async def delete_box(box_id: int, conn: aiosqlite.Connection = Depends(db_conn)):
    """Remove a box and its scan data. Vector store, DB, and local files are cleaned up."""
    cursor = await conn.execute("SELECT id, video_filename FROM boxes WHERE id = ?", (box_id,))
    row = await cursor.fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Box not found")
    video_filename = row[1]
    # Remove from vector store so search no longer returns this box
    store = get_vector_store()
    store.delete_box(box_id)
    # Delete box (CASCADE removes box_contents)
    await conn.execute("DELETE FROM boxes WHERE id = ?", (box_id,))
    await conn.commit()
    # Optional: remove uploaded video and frames from disk
    if video_filename:
        video_path = settings.uploads_dir / video_filename
        if video_path.exists():
            try:
                video_path.unlink()
            except OSError:
                pass
    frame_dir = settings.frames_dir / str(box_id)
    if frame_dir.is_dir():
        try:
            for f in frame_dir.iterdir():
                f.unlink()
            frame_dir.rmdir()
        except OSError:
            pass


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
    try:
        # Extract frames
        vp = VideoProcessor()
        frames = vp.extract_frames(video_path, box_id, max_frames=10)
        if not frames:
            raise HTTPException(status_code=400, detail="Could not extract frames from video")
        # Per-scan quality report
        diagnostics = compute_capture_diagnostics(frames)
        # Describe frames (vision) — per-frame errors are handled; we get one caption per frame or fallback
        vs = VisionService()
        raw_descriptions = vs.describe_frames(frames)
        if not raw_descriptions:
            raise HTTPException(
                status_code=400,
                detail="Could not describe any frames. Check that the video has visible content and try again.",
            )
        # Clean up captions and drop empty so we only store and embed usable content
        descriptions = [d for d in (_normalize_caption(t) for t in raw_descriptions) if d and d.strip()]
        if not descriptions:
            raise HTTPException(
                status_code=400,
                detail="No objects could be identified in the video. Try better lighting, a longer scan (5–10 seconds), or a different video.",
            )
        # Add a label-aware document so search by box label (e.g. "box 1") matches this box
        label_doc = f'Box labeled "{box_label}". Contents: ' + (descriptions[0] if descriptions else "various items.")
        texts_for_store = descriptions + [label_doc]
        es = EmbeddingService()
        embeddings = es.embed(texts_for_store)
        store = get_vector_store()
        store.add(box_id, box_label, texts_for_store, embeddings)
        # Store contents for display (replace any previous)
        await conn.execute("DELETE FROM box_contents WHERE box_id = ?", (box_id,))
        for text in descriptions:
            await conn.execute("INSERT INTO box_contents (box_id, item_text) VALUES (?, ?)", (box_id, text))
        # Update box record and diagnostics
        await conn.execute(
            "UPDATE boxes SET video_filename = ?, scan_frame_count = ?, scan_brightness = ?, scan_blur_score = ?, updated_at = datetime('now') WHERE id = ?",
            (safe_name, diagnostics["frame_count"], diagnostics["brightness"], diagnostics["blur_score"], box_id),
        )
        await conn.commit()
        return await get_box(box_id, conn)
    except HTTPException:
        raise
    except Exception as e:
        import logging
        logging.getLogger(__name__).exception("Video upload processing failed")
        raise HTTPException(
            status_code=500,
            detail=f"Processing failed: {str(e)}. Check server logs for details.",
        )
