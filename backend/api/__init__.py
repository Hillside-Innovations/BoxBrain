from .boxes import router as boxes_router
from .locations import router as locations_router
from .meta import router as meta_router
from .search import router as search_router

__all__ = ["boxes_router", "locations_router", "meta_router", "search_router"]
