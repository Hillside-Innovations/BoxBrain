from fastapi import APIRouter, Query

from services import EmbeddingService
from services.vector_store import get_vector_store


router = APIRouter(prefix="/search", tags=["search"])


@router.get("")
async def search(q: str = Query(..., min_length=1)):
    """Semantic search: returns matching boxes with scores (e.g. 'allen key' matches 'hex wrench')."""
    es = EmbeddingService()
    query_embedding = es.embed([q])[0]
    store = get_vector_store()
    hits = store.search(query_embedding, n_results=10)
    return {
        "query": q,
        "results": [
            {"box_id": bid, "box_label": label, "score": round(score, 4)}
            for bid, label, score in hits
        ],
    }
