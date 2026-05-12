"""Word service - business logic for word operations."""
from models.database import get_db


async def get_words(category: str = "", search: str = "", page: int = 1, page_size: int = 50):
    db = await get_db()
    conditions = []
    params = []

    if category:
        conditions.append("category = ?")
        params.append(category)
    if search:
        conditions.append("(word LIKE ? OR meaning_cn LIKE ?)")
        params.extend([f"%{search}%", f"%{search}%"])

    where = f"WHERE {' AND '.join(conditions)}" if conditions else ""

    # Get total count
    count_row = await db.execute(f"SELECT COUNT(*) FROM words {where}", params)
    total = (await count_row.fetchone())[0]

    # Get paginated results
    offset = (page - 1) * page_size
    cursor = await db.execute(
        f"SELECT * FROM words {where} ORDER BY frequency_rank LIMIT ? OFFSET ?",
        params + [page_size, offset]
    )
    rows = await cursor.fetchall()

    words = [dict(row) for row in rows]
    return {"words": words, "total": total, "page": page, "page_size": page_size}


async def get_word(word_id: int):
    db = await get_db()
    cursor = await db.execute("SELECT * FROM words WHERE id = ?", (word_id,))
    row = await cursor.fetchone()
    return dict(row) if row else None


async def get_categories():
    db = await get_db()
    cursor = await db.execute(
        "SELECT category, COUNT(*) as count FROM words GROUP BY category ORDER BY category"
    )
    rows = await cursor.fetchall()
    return [{"category": row[0], "count": row[1]} for row in rows]


async def get_word_count():
    db = await get_db()
    cursor = await db.execute("SELECT COUNT(*) FROM words")
    return (await cursor.fetchone())[0]
