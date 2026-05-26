"""Favorite words service - user bookmarks for words."""
from datetime import datetime
from models.database import get_db
from services.word_service import _parse_word


async def add_favorite(user_id: int, word_id: int):
    """Add a word to user's favorites."""
    db = await get_db()
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    await db.execute(
        "INSERT OR IGNORE INTO favorite_words (user_id, word_id, created_at, updated_at) VALUES (?, ?, ?, ?)",
        (user_id, word_id, now, now)
    )
    await db.commit()


async def remove_favorite(user_id: int, word_id: int):
    """Remove a word from user's favorites."""
    db = await get_db()
    await db.execute(
        "DELETE FROM favorite_words WHERE user_id = ? AND word_id = ?",
        (user_id, word_id)
    )
    await db.commit()


async def is_favorite(user_id: int, word_id: int) -> bool:
    """Check if a word is in user's favorites."""
    db = await get_db()
    cursor = await db.execute(
        "SELECT 1 FROM favorite_words WHERE user_id = ? AND word_id = ?",
        (user_id, word_id)
    )
    return await cursor.fetchone() is not None


async def get_favorites(user_id: int, page: int = 1, page_size: int = 50):
    """Get paginated list of user's favorite words."""
    db = await get_db()

    count_row = await db.execute(
        "SELECT COUNT(*) FROM favorite_words WHERE user_id = ?", (user_id,)
    )
    total = (await count_row.fetchone())[0]

    offset = (page - 1) * page_size
    cursor = await db.execute(
        """SELECT fw.word_id, fw.created_at
           FROM favorite_words fw
           WHERE fw.user_id = ?
           ORDER BY fw.created_at DESC
           LIMIT ? OFFSET ?""",
        (user_id, page_size, offset)
    )
    rows = await cursor.fetchall()

    if not rows:
        return {"words": [], "total": total, "page": page, "page_size": page_size}

    word_ids = [r[0] for r in rows]
    fav_created_map = {r[0]: r[1] for r in rows}

    # Batch fetch word details
    placeholders = ",".join("?" * len(word_ids))
    cursor = await db.execute(
        f"SELECT * FROM words WHERE id IN ({placeholders})", word_ids
    )
    word_rows = await cursor.fetchall()
    word_map = {row["id"]: _parse_word(dict(row)) for row in word_rows}

    words = []
    for wid in word_ids:
        w = word_map.get(wid)
        if w:
            w["favorited_at"] = fav_created_map.get(wid, "")
            words.append(w)

    return {"words": words, "total": total, "page": page, "page_size": page_size}


async def get_favorite_word_ids(user_id: int) -> set[int]:
    """Get set of favorite word IDs for a user (for marking in lists)."""
    db = await get_db()
    cursor = await db.execute(
        "SELECT word_id FROM favorite_words WHERE user_id = ?", (user_id,)
    )
    return {row[0] for row in await cursor.fetchall()}
