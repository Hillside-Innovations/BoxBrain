"""In-memory vector store (numpy). Used when ChromaDB is unavailable (e.g. Python 3.14). Same interface as ChromaStore."""
from typing import List, Tuple

import numpy as np

from config import settings


class MemoryVectorStore:
    """Same add/search interface as ChromaStore; no persistence. Good for dev/CI."""

    def __init__(self) -> None:
        self._embeddings: List[np.ndarray] = []
        self._box_ids: List[int] = []
        self._box_labels: List[str] = []

    def delete_box(self, box_id: int) -> None:
        """Remove all vectors for this box (e.g. when box is deleted)."""
        keep = [i for i in range(len(self._box_ids)) if self._box_ids[i] != box_id]
        self._embeddings = [self._embeddings[i] for i in keep]
        self._box_ids = [self._box_ids[i] for i in keep]
        self._box_labels = [self._box_labels[i] for i in keep]

    def add(self, box_id: int, box_label: str, texts: List[str], embeddings: List[List[float]]) -> None:
        if not texts or not embeddings:
            return
        self.delete_box(box_id)
        for emb in embeddings:
            self._embeddings.append(np.array(emb, dtype=np.float32))
            self._box_ids.append(box_id)
            self._box_labels.append(box_label)

    def search(self, query_embedding: List[float], n_results: int = 10) -> List[Tuple[int, str, float]]:
        """Return at most n_results boxes, aggregated over frames, with simple scoring.

        Applies a basic multi-frame evidence rule: a box is only considered a hit
        if at least `settings.search_min_frames` individual frame embeddings for
        that box exceed `settings.search_frame_score_threshold`.
        """
        if not self._embeddings:
            return []

        q = np.array(query_embedding, dtype=np.float32).reshape(1, -1)
        vecs = np.stack(self._embeddings, axis=0)
        # Cosine similarity (assume normalized in sentence-transformers)
        raw_scores = np.dot(vecs, q.T).flatten()

        # Track per-box best score (cosine in [-1, 1]) and how many frames are "strong"
        best_by_box: dict[int, float] = {}
        count_strong_by_box: dict[int, int] = {}

        for idx, raw in enumerate(raw_scores):
            bid = self._box_ids[idx]
            best_by_box[bid] = max(best_by_box.get(bid, -1.0), float(raw))

            # Normalize cosine sim [-1,1] to score [0,1] for per-frame thresholding
            norm = (max(-1.0, min(1.0, float(raw))) + 1.0) / 2.0
            if norm >= settings.search_frame_score_threshold:
                count_strong_by_box[bid] = count_strong_by_box.get(bid, 0) + 1

        # Filter boxes that don't have enough strong frames
        eligible_box_ids = [
            bid
            for bid, best in best_by_box.items()
            if count_strong_by_box.get(bid, 0) >= settings.search_min_frames
        ]
        if not eligible_box_ids:
            return []

        # Get label from first occurrence
        label_by_id = {}
        for bid, lbl in zip(self._box_ids, self._box_labels):
            if bid not in label_by_id:
                label_by_id[bid] = lbl

        # Build (box_id, label, normalized_score) and sort by score desc
        results: List[Tuple[int, str, float]] = []
        for bid in eligible_box_ids:
            raw = best_by_box[bid]
            norm = (max(-1.0, min(1.0, float(raw))) + 1.0) / 2.0
            results.append((bid, label_by_id[bid], float(norm)))

        results.sort(key=lambda x: -x[2])
        return results[:n_results]
