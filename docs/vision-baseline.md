# Vision pipeline baseline

Recorded runs of the vision test harness (`python -m tests.vision_harness --search`) for tracking performance and search quality over time. Use the same fixtures (videos in DB) when re-running so results are comparable.

**How to run:** From `backend/`, with real vision (no `MOCK_VISION`):

```bash
cd backend && python -m tests.vision_harness --search
```

Optional: capture output and time:

```bash
cd backend && time python -m tests.vision_harness --search 2>&1 | tee docs/vision-harness-$(date +%Y%m%d).log
```

---

## Baseline runs

### 2026-03-06 (initial)

- **Fixtures:** 5 boxes with video (box_id 8–12, labels "box 1"–"box 5")
- **Frames:** 7 + 5 + 5 + 10 + 10 = 37 total
- **Stack:** BLIP (Salesforce/blip-image-captioning-base), sentence-transformers (all-MiniLM-L6-v2), ChromaDB
- **Total time:** ~26–27 s (vision + embed + index + search)
- **Search benchmark:** Query = box label; top result only.

| Query   | Top result        | Score  |
|---------|-------------------|--------|
| 'box 1' | box_id=9 (box 2)  | 0.774  |
| 'box 2' | box_id=9 (box 2)  | 0.768  |
| 'box 3' | box_id=9 (box 2)  | 0.772  |
| 'box 4' | box_id=12 (box 5)| 0.761  |
| 'box 5' | box_id=12 (box 5)| 0.759  |

**Notes:** Search-by-label correct 3/5 (box 2, 4, 5). "box 1" and "box 3" ranked "box 2" first—expected when querying by label only, since BLIP captions describe scene content.

---

## Adding a new run

1. Run the harness (with or without `tee` for logs).
2. Copy the "Search benchmark" table and any timing notes.
3. Add a new **### YYYY-MM-DD** section above this line, with:
   - Fixtures (count, box_ids/labels if useful)
   - Frames total
   - Stack (if changed: e.g. different vision model or embedder)
   - Total time
   - Search benchmark table
   - Short notes (e.g. "after switching to BLIP-2", "Python 3.12", "with GPU")
