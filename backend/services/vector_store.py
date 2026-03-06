"""Vector store abstraction: ChromaDB when available, else in-memory (numpy) for compatibility."""
from typing import List, Optional, Tuple

from config import settings

_store = None


def _try_chroma() -> Optional["ChromaStore"]:
    try:
        from .chroma_store import ChromaStore
        return ChromaStore()
    except Exception:
        return None


def _make_memory_store():
    from .memory_vector_store import MemoryVectorStore
    return MemoryVectorStore()


def get_vector_store():
    """Return ChromaStore if ChromaDB works (e.g. Python 3.11/3.12), else singleton MemoryVectorStore."""
    global _store
    if _store is not None:
        return _store
    store = _try_chroma()
    if store is not None:
        _store = store
        return _store
    _store = _make_memory_store()
    return _store
