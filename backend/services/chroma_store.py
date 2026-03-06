"""ChromaDB vector store: embeddings keyed by box_id for semantic search. Local persistence."""
from pathlib import Path
from typing import List, Tuple

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

    def add(self, box_id: int, box_label: str, texts: List[str], embeddings: List[List[float]]) -> None:
        if not texts or not embeddings:
            return
        # Replace any existing content for this box (re-upload)
        try:
            self._collection.delete(where={"box_id": box_id})
        except Exception:
            pass
        ids = [f"box_{box_id}_{i}" for i in range(len(texts))]
        metadatas = [{"box_id": box_id, "box_label": box_label} for _ in texts]
        self._collection.add(ids=ids, embeddings=embeddings, documents=texts, metadatas=metadatas)

    def search(self, query_embedding: List[float], n_results: int = 10) -> List[Tuple[int, str, float]]:
        count = self._collection.count()
        if count == 0:
            return []
        results = self._collection.query(
            query_embeddings=[query_embedding],
            n_results=min(n_results, count),
            include=["metadatas", "distances"],
        )
        if not results or not results["metadatas"] or not results["metadatas"][0]:
            return []
        out = []
        seen_box_ids = set()
        for meta, dist in zip(results["metadatas"][0], results["distances"][0]):
            box_id = meta["box_id"]
            box_label = meta["box_label"]
            if box_id in seen_box_ids:
                continue
            seen_box_ids.add(box_id)
            # Chroma returns L2 distance; lower = more similar. Convert to simple score for API (1 / (1 + d))
            score = 1.0 / (1.0 + float(dist))
            out.append((box_id, box_label, score))
        return out
