"""
Vision pipeline test harness.

Uses videos already in the DB as fixtures: for each box with a video_filename,
runs frame extraction and vision (BLIP or mock), then optionally runs search
with canned queries and reports results.

Run from backend dir:
  python -m tests.vision_harness              # vision only
  python -m tests.vision_harness --search      # vision + search benchmark (labels + content-based)
  MOCK_VISION=1 python -m tests.vision_harness # use mock vision (no BLIP download)

Content-based queries: derived from BLIP descriptions (query with a box's own
caption, expect that box to rank) and optionally from tests/vision_content_queries.json
([{"query": "screwdriver", "expected_box_id": 10}, ...]).

Requires: ffmpeg on PATH. Uses config.settings (data dir, DB, uploads).
"""
import argparse
import json
import sqlite3
import sys
from pathlib import Path
from typing import List, Tuple

# Ensure backend is on path when run as __main__
if __name__ == "__main__":
    _backend = Path(__file__).resolve().parent.parent
    if str(_backend) not in sys.path:
        sys.path.insert(0, str(_backend))

from config import settings
from services import VideoProcessor, VisionService, EmbeddingService
from services.vector_store import get_vector_store


def load_video_fixtures_from_db() -> List[Tuple[int, str, Path]]:
    """Return list of (box_id, label, video_path) for boxes that have a video file on disk."""
    fixtures: List[Tuple[int, str, Path]] = []
    conn = sqlite3.connect(str(settings.db_path))
    try:
        conn.row_factory = sqlite3.Row
        cur = conn.execute(
            "SELECT id, label, video_filename FROM boxes WHERE video_filename IS NOT NULL AND video_filename != ''"
        )
        for row in cur.fetchall():
            box_id = row["id"]
            label = row["label"]
            video_filename = row["video_filename"]
            video_path = settings.uploads_dir / video_filename
            if video_path.exists():
                fixtures.append((box_id, label, video_path))
            else:
                print(f"[skip] box_id={box_id} label={label!r}: video not found {video_path}", file=sys.stderr)
    finally:
        conn.close()
    return fixtures


def run_vision_harness(
    fixtures: List[Tuple[int, str, Path]],
    out_frames_dir: Path,
    run_search: bool = False,
) -> List[Tuple[int, str, List[str]]]:
    """
    Run frame extraction + vision on each fixture. Optionally run search benchmark.
    Returns list of (box_id, label, descriptions).
    """
    vp = VideoProcessor()
    vs = VisionService()
    results: List[Tuple[int, str, List[str]]] = []

    for box_id, label, video_path in fixtures:
        frame_dir = out_frames_dir / str(box_id)
        frame_dir.mkdir(parents=True, exist_ok=True)
        frames = vp.extract_frames(video_path, box_id, max_frames=10, out_dir=frame_dir)
        if not frames:
            print(f"[warn] box_id={box_id}: no frames extracted", file=sys.stderr)
            results.append((box_id, label, []))
            continue
        descriptions = vs.describe_frames(frames)
        results.append((box_id, label, descriptions))
        print(f"  box_id={box_id} label={label!r} frames={len(frames)} descriptions={len(descriptions)}")

    if run_search and results:
        store = get_vector_store()
        es = EmbeddingService()
        # Re-index fixture boxes into the store (by box_id and label)
        for box_id, label, descriptions in results:
            if not descriptions:
                continue
            store.delete_box(box_id)  # clear any previous
            # Add label-aware document so label queries (e.g. "box 1") match this box
            label_doc = f'Box labeled "{label}". Contents: ' + (descriptions[0] if descriptions else "various items.")
            texts_for_store = descriptions + [label_doc]
            embeddings = es.embed(texts_for_store)
            store.add(box_id, label, texts_for_store, embeddings)
        # Label-based: query with box label, report top result
        canned = [label for _, label, _ in results if label][:5]
        print("\nSearch benchmark — label queries (top result per query):")
        for q in canned:
            emb = es.embed([q])
            hits = store.search(emb[0], n_results=3)
            if hits:
                top = hits[0]
                print(f"  q={q!r} -> box_id={top[0]} label={top[1]!r} score={top[2]:.3f}")
            else:
                print(f"  q={q!r} -> (no results)")

        # Content-based: query with BLIP description from each box, expect that box in top-3
        print("\nSearch benchmark — content-based queries (query = first BLIP caption per box):")
        content_ok = 0
        content_total = 0
        for box_id, label, descriptions in results:
            if not descriptions:
                continue
            query = descriptions[0].strip()
            if len(query) > 60:
                query = query[:57] + "..."
            content_total += 1
            emb = es.embed([query])
            hits = store.search(emb[0], n_results=3)
            if hits:
                top = hits[0]
                in_top3 = any(h[0] == box_id for h in hits)
                if in_top3:
                    content_ok += 1
                status = "PASS" if top[0] == box_id else ("top-3" if in_top3 else "FAIL")
                print(f"  q={query!r} (expected box_id={box_id}) -> top box_id={top[0]} score={top[2]:.3f} [{status}]")
            else:
                print(f"  q={query!r} (expected box_id={box_id}) -> (no results) [FAIL]")
        if content_total:
            print(f"  Content-based: {content_ok}/{content_total} expected box in top-3")

        # Optional hand-picked content queries from JSON
        queries_file = Path(__file__).resolve().parent / "vision_content_queries.json"
        if queries_file.exists():
            try:
                with open(queries_file) as f:
                    extra = json.load(f)
            except Exception as e:
                print(f"\n[skip] Could not load {queries_file}: {e}", file=sys.stderr)
                extra = []
            if isinstance(extra, list) and extra:
                print("\nSearch benchmark — hand-picked content queries (vision_content_queries.json):")
                for item in extra:
                    if isinstance(item, dict) and "query" in item and "expected_box_id" in item:
                        q = item["query"]
                        expected = item["expected_box_id"]
                        emb = es.embed([q])
                        hits = store.search(emb[0], n_results=3)
                        if hits:
                            top = hits[0]
                            in_top3 = any(h[0] == expected for h in hits)
                            status = "PASS" if top[0] == expected else ("top-3" if in_top3 else "FAIL")
                            print(f"  q={q!r} (expected box_id={expected}) -> top box_id={top[0]} score={top[2]:.3f} [{status}]")
                        else:
                            print(f"  q={q!r} (expected box_id={expected}) -> (no results) [FAIL]")

    return results


def main() -> int:
    parser = argparse.ArgumentParser(description="Vision pipeline harness using DB videos as fixtures")
    parser.add_argument("--search", action="store_true", help="Run search benchmark after vision")
    parser.add_argument(
        "--out-dir",
        type=lambda p: Path(p),
        default=None,
        help="Directory for extracted frames (default: data/harness_frames)",
    )
    args = parser.parse_args()

    fixtures = load_video_fixtures_from_db()
    if not fixtures:
        print("No video fixtures found. Upload at least one box video (via the app or API).", file=sys.stderr)
        return 1

    out_frames_dir = args.out_dir or (settings.data_dir / "harness_frames")
    out_frames_dir.mkdir(parents=True, exist_ok=True)
    print(f"Fixtures: {len(fixtures)} boxes with video. Frames out dir: {out_frames_dir}")
    print("Running vision (extract_frames + describe_frames)...")
    run_vision_harness(fixtures, out_frames_dir, run_search=args.search)
    print("Done.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
