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

**Benchmarks:** With `--search`, the harness reports (1) **label queries** — query by box label, top result; (2) **content-based queries** — query by each box’s first BLIP caption, expect that box in top-3 (PASS/top-3/FAIL); (3) **hand-picked content queries** — if `backend/tests/vision_content_queries.json` exists, format `[{"query": "screwdriver", "expected_box_id": 10}, ...]`, same PASS/top-3/FAIL reporting.

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

**Score:** Similarity between the query embedding and the top-matching box (aggregated over its frame embeddings). Value in [0, 1]; higher means the box’s indexed content is more similar to the query. From our embedder (sentence-transformers) and vector store, this is effectively cosine similarity normalized to that range.

**Notes:** Search-by-label correct 3/5 (box 2, 4, 5). "box 1" and "box 3" ranked "box 2" first—expected when querying by label only, since BLIP captions describe scene content.

### 2026-03-06 (re-run, same fixtures)

- **Fixtures:** Same 5 boxes (box_id 8–12), 37 frames total.
- **Stack:** Same (BLIP, sentence-transformers, ChromaDB).
- **Total time:** 25.9 s (`time` reported).
- **Search benchmark:** Identical to initial run.

| Query   | Top result        | Score  |
|---------|-------------------|--------|
| 'box 1' | box_id=9 (box 2)  | 0.774  |
| 'box 2' | box_id=9 (box 2)  | 0.768  |
| 'box 3' | box_id=9 (box 2)  | 0.772  |
| 'box 4' | box_id=12 (box 5)| 0.761  |
| 'box 5' | box_id=12 (box 5)| 0.759  |

**Comparison:** Results are reproducible. Time (~26 s vs ~25.9 s) and all search scores match the initial baseline; no code or model change between runs.

---

## Performance improvements

Ways to speed up the vision pipeline (and re-measure with the harness):

| Area | Option | Trade-off |
|------|--------|-----------|
| **Hardware** | Use a **GPU** (CUDA). BLIP and sentence-transformers both use `.to("cuda")` when available. | Biggest win on CPU-bound runs; no code change. |
| **Frames** | Reduce **max_frames** (e.g. 5 instead of 10) in `VideoProcessor.extract_frames` or the harness. | Fewer frames → faster vision/embed, slightly less coverage. |
| **Frame extraction** | **ffmpeg**: lower resolution (`-vf "scale=224:224,fps=1"`) or higher `-q:v` (e.g. 5) for smaller JPEGs. | Slightly faster I/O and a bit faster BLIP; possible quality loss. |
| **Vision model** | Swap BLIP for a **smaller/faster** captioning model (e.g. smaller BLIP variant, or a distilled model). | Need to re-baseline quality; may reduce caption quality. |
| **Vision batch** | **BLIP image-captioning** has a known limitation: batch size > 1 often errors. So we stay per-frame. | If you switch to another model that supports batch inference, process frames in batches (e.g. 4–8) for better GPU use. |
| **Embeddings** | sentence-transformers already batches internally. Could try a **smaller embedder** (e.g. all-MiniLM-L6-v2 is already small). | Minor; embed time is usually small vs BLIP. |
| **Harness** | Run fixtures in **parallel** (e.g. one process per video) to use multiple cores. | More complex; good for many boxes. |

Re-run the harness after any change and add a new baseline run to compare time and search results.

---

## Adding a new run

1. Run the harness (with or without `tee` for logs).
2. Copy the "Search benchmark — label queries" table, the "content-based queries" summary (and sample lines if useful), any "hand-picked content queries" output, and timing notes.
3. Add a new **### YYYY-MM-DD** section above this line, with:
   - Fixtures (count, box_ids/labels if useful)
   - Frames total
   - Stack (if changed: e.g. different vision model or embedder)
   - Total time
   - Search benchmark table
   - Short notes (e.g. "after switching to BLIP-2", "Python 3.12", "with GPU")
