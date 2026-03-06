"""ChromaDB vector store: embeddings keyed by box_id for semantic search. Local persistence."""
from pathlib import Path
from typing import Dict, List, Tuple

import chromadb
from chromadb.config import Settings as ChromaSettings

from config import settings


class ChromaStore:
    def __init__(self) -> None:
        self.path = Path(settings.chroma_path)
        self.path.mkdir(parents=True, exist_ok=True)
        self._client = chromadb.PersistentClient(
            path=str(self.path),
            settings=ChromaSettings(anonymized_telemetry=False),
        )
        self._collection = self._client.get_or_create_collection(
            "box_contents",
            metadata={"description": "Text descriptions of box contents for semantic search"},
        )

    def delete_box(self, box_id: int) -> None:
        """Remove all vectors for this box (e.g. when box is deleted)."""
        try:
            self._collection.delete(where={"box_id": box_id})
        except Exception:
            pass

    def add(self, box_id: int, box_label: str, texts: List[str], embeddings: List[List[float]]) -> None:
        if not texts or not embeddings:
            return
        # Replace any existing content for this box (re-upload)
        self.delete_box(box_id)
        ids = [f"box_{box_id}_{i}" for i in range(len(texts))]
        metadatas = [{"box_id": box_id, "box_label": box_label} for _ in texts]
        self._collection.add(ids=ids, embeddings=embeddings, documents=texts, metadatas=metadatas)

    def search(self, query_embedding: List[float], n_results: int = 10) -> List[Tuple[int, str, float]]:
        """Return at most n_results boxes, aggregated over frames, with simple scoring.

        Applies a basic multi-frame evidence rule: a box is only considered a hit
        if at least `settings.search_min_frames` individual frame embeddings for
        that box exceed `settings.search_frame_score_threshold`.
        """
        count = self._collection.count()
        if count == 0:
            return []

        # We store at most ~10 frames per box, so requesting n_results per-frame
        # results is enough to see all frames for all boxes in practice.
        raw = self._collection.query(
            query_embeddings=[query_embedding],
            n_results=min(max(n_results * 4, n_results), count),
            include=["metadatas", "distances"],
        )
        if not raw or not raw["metadatas"] or not raw["metadatas"][0]:
            return []

        best_by_box: Dict[int, float] = {}
        count_strong_by_box: Dict[int, int] = {}
        label_by_id: Dict[int, str] = {}

        for meta, dist in zip(raw["metadatas"][0], raw["distances"][0]):
            box_id = meta["box_id"]
            box_label = meta["box_label"]
            label_by_id.setdefault(box_id, box_label)

            # Chroma returns L2 distance; lower = more similar. Convert to score [0,1].
            score = 1.0 / (1.0 + float(dist))
            best_by_box[box_id] = max(best_by_box.get(box_id, 0.0), score)
            if score >= settings.search_frame_score_threshold:
                count_strong_by_box[box_id] = count_strong_by_box.get(box_id, 0) + 1

        eligible_box_ids = [
            bid
            for bid, best in best_by_box.items()
            if count_strong_by_box.get(bid, 0) >= settings.search_min_frames
            or best >= settings.search_strong_match_score
        ]
        if not eligible_box_ids:
            return []

        results: List[Tuple[int, str, float]] = [
            (bid, label_by_id[bid], best_by_box[bid]) for bid in eligible_box_ids
        ]
        results.sort(key=lambda x: -x[2])
        return results[:n_results]
