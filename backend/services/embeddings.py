"""Local text embeddings via sentence-transformers (open-source)."""
from typing import List

from sentence_transformers import SentenceTransformer


class EmbeddingService:
    _model: SentenceTransformer | None = None

    def _get_model(self) -> SentenceTransformer:
        if EmbeddingService._model is None:
            EmbeddingService._model = SentenceTransformer("all-MiniLM-L6-v2")
        return EmbeddingService._model

    def embed(self, texts: List[str]) -> List[List[float]]:
        if not texts:
            return []
        model = self._get_model()
        return model.encode(texts, convert_to_numpy=True).tolist()
