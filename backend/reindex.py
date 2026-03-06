"""Reindex vector store from persisted box_contents so search works after backend restart."""
import aiosqlite

from database import get_db
from services import EmbeddingService
from services.vector_store import get_vector_store


async def reindex_vector_store() -> int:
    """Load all box contents from DB, embed, and add to vector store. Returns number of boxes reindexed."""
    conn = await get_db()
    try:
        cursor = await conn.execute(
            "SELECT b.id, b.label FROM boxes b INNER JOIN box_contents c ON b.id = c.box_id GROUP BY b.id, b.label"
        )
        rows = await cursor.fetchall()
        if not rows:
            return 0
        es = EmbeddingService()
        store = get_vector_store()
        count = 0
        for row in rows:
            box_id, label = row[0], row[1]
            cur = await conn.execute("SELECT item_text FROM box_contents WHERE box_id = ? ORDER BY rowid", (box_id,))
            texts = [r[0] for r in await cur.fetchall()]
            if not texts:
                continue
            # Add label-aware document so search by box label matches this box
            label_doc = f'Box labeled "{label}". Contents: ' + ("; ".join(texts[:5]) if texts else "various items.")
            texts_with_label = texts + [label_doc]
            embeddings = es.embed(texts_with_label)
            store.add(box_id, label, texts_with_label, embeddings)
            count += 1
        return count
    finally:
        await conn.close()
