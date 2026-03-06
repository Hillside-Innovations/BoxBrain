# BoxBrain

**A memory system for the physical world.** Search for an item in plain language and get back which box, bin, shelf, or room it’s in—no typing lists or keeping inventory.

---

## The problem

People don’t lose their stuff; they lose the memory of where it is. Moves, renovations, storage, garages, and job sites break that mental map. The result: duplicate buys, hours of searching, stalled projects, and “mystery boxes” that never get opened.

Existing tools assume you’ll type and organize everything. When you’re packing or in the middle of a project, that doesn’t happen.

## The approach

Instead of asking you to describe what’s in a box, BoxBrain **watches**. You number a box, record a short video of the open box, and close it. AI detects what’s inside; those items become searchable. Later you search—“allen key”, “passport”, “Makita battery”—and get the answer: **Box 27 — garage shelf.**

No manual item lists. No categories to maintain. We index **containers and locations**, not ownership or value.

---

## How it works (MVP)

1. **Label a box** (e.g. `attic_underscore_1`).
2. **Record a 5–10 second video** of the open box.
3. **AI identifies objects** in the footage (tools, parts, paperwork, hardware, etc.).
4. **Items are indexed** for semantic search (e.g. “allen key” matches “hex wrench”).
5. **Search** returns the box (and location) that contains the item.

All components run **locally** on one machine for the MVP.

## Tech stack

| Role | Technology |
|------|------------|
| Frontend | React + Vite (mobile-first web app) |
| Backend | Python FastAPI |
| Media | ffmpeg (frame extraction from video) |
| Vision | Multimodal AI (object detection in frames) |
| Search | Text embeddings + ChromaDB (vector/semantic search) |
| Data | SQLite (boxes and metadata) |

---

## Running locally

**Prerequisites:** Node.js, Python 3.11+, ffmpeg (see [backend/README.md](backend/README.md)). One-time setup: install backend deps (`cd backend && python -m venv .venv && pip install -r requirements.txt`) and frontend deps (`cd frontend && npm install`).

**Start everything (backend + frontend):**

- **macOS / Linux:** `./scripts/start.sh`
- **Windows (PowerShell):** `.\scripts\start.ps1` (uses `backend\.venv\Scripts\python.exe`; no `activate` needed)

- Backend: http://127.0.0.1:8000 (API and [docs](http://127.0.0.1:8000/docs))
- Frontend: http://localhost:5173

The script starts the backend with the real vision model (BLIP); the first video upload may download ~1GB if not cached. To use placeholder descriptions instead, run the backend with `MOCK_VISION=1` (see backend/README.md). Press **Ctrl+C** to stop both.

To run backend and frontend separately, see [backend/README.md](backend/README.md) and [frontend/README.md](frontend/README.md).

---

## Success criteria (v1)

- User packs **20+ boxes** with normal, messy packing.
- User can **correctly find an item in under 15 seconds** at least **70%** of the time.

Validation uses real packed boxes and blind search tests—not just unit tests—because vision systems that look good in clean demos often fail in real garages and basements.

## Differentiation

- **Existing tools** = digital filing cabinets (catalog possessions, need manual entry).
- **BoxBrain** = externalized spatial memory (observe containers, auto-detect, answer “Where is ___?”).

Zero manual entry, usable in chaotic situations (moves, renovations), and demonstrable in seconds. If search reliably returns the right container, the product fills a gap no current app owns.

---

## Documentation

Detailed product and design docs live in **`/docs`**:

- **[whitepaper.md](docs/whitepaper.md)** — Vision, problem, insight, MVP workflow, success criteria, future expansion
- **[competitive-analysis.md](docs/competitive-analysis.md)** — Landscape, gap, differentiation, strategic position
- **[mvp-definition.md](docs/mvp-definition.md)** — Measurable v1 success
- **[tech-stack.md](docs/tech-stack.md)** — Components and roles
- **[testing-plan.md](docs/testing-plan.md)** — Real-world validation approach
- **[api-for-frontend.md](docs/api-for-frontend.md)** — API contract and examples for frontend integration

---

*In one sentence: we’re building **Google for your stuff**.*
