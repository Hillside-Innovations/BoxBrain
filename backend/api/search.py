from fastapi import APIRouter, Query

from config import settings
from services import EmbeddingService
from services.vector_store import get_vector_store


router = APIRouter(prefix="/search", tags=["search"])


@router.get("")
async def search(q: str = Query(..., min_length=1)):
    """Semantic search: returns matching boxes with scores (e.g. 'allen key' matches 'hex wrench')."""
    es = EmbeddingService()
    query_embedding = es.embed([q])[0]
    store = get_vector_store()
    hits = store.search(query_embedding, n_results=20)

    # Apply a simple decision layer: if no result is confidently above the
    # configured threshold, or if the top two hits are too close together,
    # treat this as "no confident match" and return an empty list.
    if not hits:
        filtered = []
    else:
        # Absolute score threshold.
        strong = [h for h in hits if h[2] >= settings.search_min_score]
        if not strong:
            filtered = []
        else:
            strong.sort(key=lambda h: -h[2])
            top_score = strong[0][2]
            second_score = strong[1][2] if len(strong) > 1 else None
            if second_score is not None and top_score - second_score < settings.search_min_score_delta:
                # Ambiguous: top and second-best are nearly tied; avoid overconfident guesses.
                filtered = []
            else:
                filtered = strong

    return {
        "query": q,
        "results": [
            {"box_id": bid, "box_label": label, "score": round(score, 4)}
            for bid, label, score in filtered
        ],
    }
