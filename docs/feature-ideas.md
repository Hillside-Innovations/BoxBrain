# Feature ideas and future directions

This file collects possible features beyond the MVP. It is a grab bag of ideas, **not** a committed roadmap.

## UX and workflow

- **Better capture guidance**: inline tips during recording (e.g. “move slower”, “get all corners”).
- **Capture checklist**: quick checklist per box (“lid off”, “box number visible”, “no glare”).
- **Search history**: recent searches, pinned queries.
- **Confidence indicators**: show when a result is “very confident” vs “uncertain, check nearby boxes”.
- **Multi-hit view**: show when an item is likely in multiple boxes (with scores and locations).
- **Explainability view**: let users inspect *why* the app thinks an item is in a box/container (e.g. show example frames, captions, and matching phrases that led to the result).

## Vision and search quality

- **Higher‑quality vision model**: swap or augment BLIP with a stronger object detection / captioning model.
- **Active re‑scan prompts**: suggest re‑scanning boxes with low‑quality frames (blur, darkness, etc.).
- **Attribute enrichment**: derive attributes like “tool”, “paperwork”, “electronics” to help ranking.
- **Hard negative mining**: use misfires from real tests to retrain/improve search.
- **Read handwritten box labels**: use vision to read the physical label written on the box and propose it as the box name in the UI (with easy override).

## Box and location management

- **Box status**: mark boxes as “packed”, “unpacked”, “donate”, “trash”.
- **Location hierarchy**: structured locations (house → room → shelf → box).
- **Shelves as first‑class locations**: represent shelves, racks, and fixed spots explicitly so search can say “garage shelf 2, left”.
- **Containers within containers**: support nesting (bin on a shelf, box inside a bigger bin) so results can show the full path, not just the outermost box.
- **Merge/split boxes**: support merging content when boxes are combined, or splitting when re‑packed.

## Devices and integrations

- **Phone camera helper**: deeper mobile integration (PWA polish, camera constraints, “scan mode”).
- **Export for backup**: export embeddings + metadata to a portable archive.
- **Home inventory bridge**: optional export to traditional inventory tools (for insurance or valuation).

## Reliability and tooling

- **Capture diagnostics**: per‑scan quality report (frame count, brightness, blur).
- **Test harness**: canned boxes + queries to benchmark changes to vision/search.
- **Sync between machines**: optional sync of the local database/chroma store across devices.

