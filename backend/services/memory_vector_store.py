"""In-memory vector store (numpy). Used when ChromaDB is unavailable (e.g. Python 3.14). Same interface as ChromaStore."""
from typing import List, Tuple

import numpy as np


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
        if not self._embeddings:
            return []
        q = np.array(query_embedding, dtype=np.float32).reshape(1, -1)
        vecs = np.stack(self._embeddings, axis=0)
        # Cosine similarity (assume normalized in sentence-transformers)
        scores = np.dot(vecs, q.T).flatten()
        # One result per box_id (best score for that box)
        by_box: dict[int, float] = {}
        for i in np.argsort(-scores):
            bid = self._box_ids[i]
            if bid not in by_box:
                by_box[bid] = float(scores[i])
                if len(by_box) >= n_results:
                    break
        # Get label from first occurrence
        label_by_id = {}
        for i, (bid, lbl) in enumerate(zip(self._box_ids, self._box_labels)):
            if bid not in label_by_id:
                label_by_id[bid] = lbl
        # Normalize cosine sim [-1,1] to score [0,1]
        return [(bid, label_by_id[bid], float((max(-1.0, min(1.0, s)) + 1) / 2)) for bid, s in sorted(by_box.items(), key=lambda x: -x[1])]
