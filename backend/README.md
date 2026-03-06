# BoxBrain Backend

Local-first FastAPI server: box CRUD, video upload (ffmpeg → frames), vision + embeddings, semantic search. No cloud required; all components run on one machine.

---

## Stack

- **FastAPI** — API
- **SQLite** (aiosqlite) — box metadata
- **ChromaDB** — vector store for semantic search (when available)
- **ffmpeg** — frame extraction from video (must be installed on system)
- **sentence-transformers** — text embeddings (all-MiniLM-L6-v2)
- **Vision** — BLIP (Salesforce/blip-image-captioning-base) or mock via `MOCK_VISION=1`

**Vector store:** ChromaDB when available (Python 3.11/3.12 recommended). On Python 3.14+ ChromaDB may be incompatible; the app falls back to an in-memory vector store (same API, no persistence across restarts).

---

## Project structure

```
backend/
├── main.py              # FastAPI app, CORS, lifespan, DB init
├── config.py            # Paths under backend/data/, MOCK_VISION
├── database.py          # SQLite (aiosqlite), boxes table
├── models/
│   └── box.py           # Pydantic: BoxCreate, BoxUpdate, BoxResponse
├── api/
│   ├── boxes.py         # CRUD + POST /boxes/{id}/video (upload → ffmpeg → vision → embed → store)
│   └── search.py        # GET /search?q=... semantic search
├── services/
│   ├── video_processor.py   # ffmpeg frame extraction (1 fps, up to 10 frames)
│   ├── vision.py            # BLIP image captioning (or mock when MOCK_VISION=1)
│   ├── embeddings.py       # sentence-transformers all-MiniLM-L6-v2
│   ├── chroma_store.py     # ChromaDB (used when it loads, e.g. Python 3.11/3.12)
│   ├── memory_vector_store.py  # In-memory vector store (same interface)
│   └── vector_store.py     # Chooses ChromaDB or in-memory (avoids ChromaDB issues on Python 3.14)
├── requirements.txt
├── .env.example
└── README.md             # This file
```

---

## Behavior

- **Boxes:** Create (label + optional location), list, get by id, patch (e.g. location).
- **Video:** Upload `.mp4`/`.mov`/`.webm`/`.avi` → ffmpeg extracts frames → vision describes each frame → embeddings → stored by box (ChromaDB or in-memory).
- **Search:** Query string → embedding → vector search → returns `box_id`, `box_label`, `score`.

---

## Setup

```bash
cd backend
python -m venv .venv
source .venv/bin/activate   # or .venv\Scripts\activate on Windows
pip install -r requirements.txt
```

Install **ffmpeg** if needed:

- macOS: `brew install ffmpeg`
- Ubuntu: `sudo apt install ffmpeg`

Optional: copy `.env.example` to `.env` and set `MOCK_VISION=1` to skip downloading the BLIP model (for quick tests).

---

## Run

From repo root:

```bash
uvicorn backend.main:app --reload --app-dir .
```

Or from `backend/`:

```bash
cd backend && uvicorn main:app --reload
```

For quick testing without BLIP (placeholder frame descriptions):

```bash
cd backend && MOCK_VISION=1 uvicorn main:app --reload
```

Data is stored under `backend/data/` (SQLite DB, ChromaDB, uploads, frames).

---

## API

| Method | Path | Description |
|--------|------|-------------|
| GET | `/health` | Health check |
| POST | `/boxes` | Create box `{"label": "attic_1", "location": "garage"}` |
| GET | `/boxes` | List all boxes |
| GET | `/boxes/{id}` | Get one box |
| PATCH | `/boxes/{id}` | Update (e.g. location) |
| POST | `/boxes/{id}/video` | Upload video (multipart); extracts frames, runs vision, embeds, stores |
| GET | `/search?q=...` | Semantic search; returns `box_id`, `box_label`, `score` |

---

## Quick test (with server running)

```bash
curl -s http://127.0.0.1:8000/health
curl -s -X POST http://127.0.0.1:8000/boxes -H "Content-Type: application/json" -d '{"label":"attic_1","location":"garage"}'
# Upload a short video (replace with your file):
curl -s -X POST http://127.0.0.1:8000/boxes/1/video -F "video=@path/to/video.mp4"
curl -s "http://127.0.0.1:8000/search?q=wrench"
```

With `MOCK_VISION=1`, searching for "box contents" will match boxes that have had a video uploaded (mock descriptions are "box contents frame N").

---

## Verified

- Health, create box, list boxes, upload test video (ffmpeg), and search returning the correct box (with `MOCK_VISION=1` and in-memory store).
- ChromaDB fails on Python 3.14 (Pydantic v1); the app falls back to an in-memory vector store so the backend still runs. Use Python 3.11 or 3.12 for ChromaDB and persistent vectors.

---

## Optional next steps

- **Real vision:** Run without `MOCK_VISION=1` so BLIP describes frame contents for better search.
- **Tests:** Add pytest for API and services.
- **Python 3.11/3.12:** Use for ChromaDB and persistent vector storage.
