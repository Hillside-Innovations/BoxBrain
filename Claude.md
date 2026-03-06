# BoxBrain — Project brief for AI coding agents

## What this project is

**BoxBrain** is a "memory system for the physical world." It lets users find which box, bin, shelf, or room an item is in by searching in natural language—no manual inventory or typing. Users film the inside of a box; AI detects objects; later they search ("allen key", "passport", "Makita battery") and get the box/location. **We are indexing containers and locations, not cataloging possessions.**

- **MVP use case:** Moving and packing. Number a box → record short video of open box → AI detects items → search returns box number.
- **Success (MVP):** User packs 20+ boxes and correctly finds an item in under 15 seconds at least 70% of the time.

Details: see `docs/whitepaper.md`, `docs/mvp-definition.md`, `docs/competitive-analysis.md`.

---

## Tech stack

| Layer | Choice | Role |
|-------|--------|------|
| Frontend | React + Vite | Mobile-first web app: create boxes, upload short video, search |
| Backend | Python FastAPI | Receives videos, manages boxes, handles search |
| Media | ffmpeg | Extract image frames from uploaded videos |
| Vision | Multimodal AI model | Analyze frames, identify objects in box |
| Search | Text embeddings + ChromaDB | Semantic search (e.g. "allen key" ≈ "hex wrench") |
| Data | SQLite | Box records and metadata |

All components run locally on one machine for the MVP. See `docs/tech-stack.md`.

---

## Repo structure (target)

```
boxbrain/
├── Claude.md           # This file — read first
├── AGENTS.md           # Agent instructions (entry point)
├── docs/               # Product and design docs (markdown)
│   ├── whitepaper.md
│   ├── competitive-analysis.md
│   ├── mvp-definition.md
│   ├── tech-stack.md
│   └── testing-plan.md
├── frontend/           # React + Vite app (to be added)
├── backend/            # FastAPI app (to be added)
└── ...
```

Use `docs/` for product and architecture decisions; don’t invent new stack or workflow without checking there.

---

## Conventions for agents

1. **Docs over assumptions** — Prefer `docs/*.md` and this file over guessing product or tech choices.
2. **MVP scope** — Optimize for: create box → upload video → extract frames → detect objects → store in ChromaDB + SQLite → search returns box. No manual item lists or categories.
3. **Local-first** — MVP runs on a single machine; no required cloud services.
4. **Testing** — Real-world validation (e.g. 30 real packed boxes, messy packing, blind search). Unit tests support that; they don’t replace it. See `docs/testing-plan.md`.
5. **Naming** — Use clear, consistent names for boxes, containers, and “location” (box/shelf/room). Prefer “box” for the primary container in the MVP.

---

## Where to look

- **Product vision, problem, differentiation:** `docs/whitepaper.md`
- **Competitors and positioning:** `docs/competitive-analysis.md`
- **Version 1 success criteria:** `docs/mvp-definition.md`
- **Stack and components:** `docs/tech-stack.md`
- **Validation and testing strategy:** `docs/testing-plan.md`

When adding code, keep the frontend in a dedicated directory (e.g. `frontend/`) and the backend in another (e.g. `backend/`), and document any new dependencies and run instructions in the repo (e.g. README or CONTRIBUTING).
