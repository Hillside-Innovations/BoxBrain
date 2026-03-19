"""
BoxBrain backend — local-first API.
Create boxes, upload video, semantic search. No cloud required.
"""
import shutil
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from database import init_db
from reindex import reindex_vector_store
from api import boxes_router, meta_router, search_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    if not shutil.which("ffmpeg"):
        print(
            "Warning: ffmpeg not found on PATH. Video upload will fail. "
            "Install ffmpeg (see backend/README.md) and restart the server.",
            flush=True,
        )
    await init_db()
    n = await reindex_vector_store()
    if n:
        print(f"Reindexed {n} box(es) into vector store for search.")
    yield
    # shutdown: nothing to close (SQLite/ChromaDB are file-based)


app = FastAPI(
    title="BoxBrain API",
    description="Memory system for the physical world. Boxes, video upload, semantic search.",
    version="0.1.0",
    lifespan=lifespan,
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(boxes_router)
app.include_router(meta_router)
app.include_router(search_router)


@app.get("/health")
async def health():
    return {"status": "ok"}
