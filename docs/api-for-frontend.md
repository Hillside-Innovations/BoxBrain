# API contract for frontend

This doc describes the BoxBrain backend API so the frontend can integrate without guessing. The backend runs locally (e.g. `http://localhost:8000` or `http://<your-lan-ip>:8000` when testing from a phone on the same WiFi). CORS is enabled for all origins.

**Base URL:** `http://<host>:8000` (no path prefix).

**Content-Type for JSON:** `application/json`.

---

## Health

**GET** `/health`

No body. Returns `200` with:

```json
{ "status": "ok" }
```

Use this to show “Backend connected” or to fail fast if the backend is down.

---

## Boxes

### Create box

**POST** `/boxes`

Body:

```json
{
  "label": "attic_1",
  "location": "garage"
}
```

- `label` (string, required): Unique per box, e.g. `attic_1`, `garage_shelf_2`.
- `location` (string, optional): Where the box lives, e.g. `garage`, `basement`.

**201** response (or **200** depending on implementation):

```json
{
  "id": 1,
  "label": "attic_1",
  "location": "garage",
  "created_at": "2026-03-06 18:17:20",
  "updated_at": "2026-03-06 18:17:20",
  "has_video": false
}
```

**409** if a box with that `label` already exists: `{ "detail": "Box with this label already exists" }`.

---

### List boxes

**GET** `/boxes`

No body. Returns **200** with an array of box objects (same shape as create response):

```json
[
  {
    "id": 1,
    "label": "attic_1",
    "location": "garage",
    "created_at": "2026-03-06 18:17:20",
    "updated_at": "2026-03-06 18:18:12",
    "has_video": true
  }
]
```

---

### Get one box

**GET** `/boxes/{id}`

Path: `id` = integer box ID.

**200** — same single-box object as above.

**404** — `{ "detail": "Box not found" }`.

---

### Update box

**PATCH** `/boxes/{id}`

Body (all optional):

```json
{ "location": "basement" }
```

**200** — updated box object.

**404** — box not found.

---

### Upload video for a box

**POST** `/boxes/{id}/video`

**Content-Type:** `multipart/form-data`. One file field; field name must be `video`.

Example (conceptual): form field `video` = file (e.g. `.mp4`, `.mov`, `.webm`, `.avi`).

- Max file size: **100 MB** (configurable). Larger uploads return **413**.
- If the file is not a supported video type, backend returns **400** with a message like `Upload must be a video file (e.g. .mp4, .mov)`.
- **404** if box `id` does not exist.
- **200** returns the updated box object (e.g. `has_video: true` after success).

Frontend flow: user selects a box, picks a short (e.g. 5–10 second) video from the phone, then POST to `POST /boxes/<id>/video` with the file in the `video` field.

---

## Search

**GET** `/search?q=<query>`

Query param `q` (required): search string, e.g. `allen key`, `passport`, `Makita battery`.

**200** response:

```json
{
  "query": "allen key",
  "results": [
    { "box_id": 3, "box_label": "garage_tools", "score": 0.87 },
    { "box_id": 1, "box_label": "attic_1", "score": 0.62 }
  ]
}
```

- `results` is ordered by relevance (highest score first).
- If nothing matches, `results` is `[]`.
- Frontend can show “Box: garage_tools” (and optionally `box_id` for linking).

---

## Error format

On 4xx/5xx the backend returns JSON like:

```json
{ "detail": "Human-readable message" }
```

Use `detail` for toast or inline error text.

---

## OpenAPI

When the backend is running, interactive docs are at:

- **Swagger UI:** `http://<host>:8000/docs`
- **ReDoc:** `http://<host>:8000/redoc`

Your friend can use these to try the API from the browser.
