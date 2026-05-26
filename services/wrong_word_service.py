"""Wrong words service - track and manage incorrectly answered words."""
import json
from datetime import datetime
from models.database import get_db
from services.word_service import _parse_word


async def record_wrong_word(user_id: int, word_id: int):
    """Record a word as answered incorrectly. Upserts wrong_words table."""
    db = await get_db()
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    await db.execute(
        """INSERT INTO wrong_words (user_id, word_id, wrong_count, last_wrong_at, created_at, updated_at)
           VALUES (?, ?, 1, ?, ?, ?)
           ON CONFLICT(user_id, word_id) DO UPDATE SET
             wrong_count = wrong_count + 1,
             last_wrong_at = ?,
             updated_at = ?""",
        (user_id, word_id, now, now, now, now, now)
    )
    await db.commit()


async def remove_wrong_word(user_id: int, word_id: int):
    """Remove a word from the wrong words list (e.g., after user masters it)."""
    db = await get_db()
    await db.execute(
        "DELETE FROM wrong_words WHERE user_id = ? AND word_id = ?",
        (user_id, word_id)
    )
    await db.commit()


async def clear_wrong_words(user_id: int):
    """Clear all wrong words for a user."""
    db = await get_db()
    await db.execute("DELETE FROM wrong_words WHERE user_id = ?", (user_id,))
    await db.commit()


async def get_wrong_words(user_id: int, page: int = 1, page_size: int = 50):
    """Get paginated list of wrong words with details, sorted by most recent wrong."""
    db = await get_db()

    count_row = await db.execute(
        "SELECT COUNT(*) FROM wrong_words WHERE user_id = ?", (user_id,)
    )
    total = (await count_row.fetchone())[0]

    offset = (page - 1) * page_size
    cursor = await db.execute(
        """SELECT ww.word_id, ww.wrong_count, ww.last_wrong_at
           FROM wrong_words ww
           WHERE ww.user_id = ?
           ORDER BY ww.last_wrong_at DESC
           LIMIT ? OFFSET ?""",
        (user_id, page_size, offset)
    )
    rows = await cursor.fetchall()

    if not rows:
        return {"words": [], "total": total, "page": page, "page_size": page_size}

    # Batch fetch word details
    word_ids = [r[0] for r in rows]
    wrong_count_map = {r[0]: r[1] for r in rows}
    last_wrong_map = {r[0]: r[2] for r in rows}

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
            w["wrong_count"] = wrong_count_map.get(wid, 1)
            w["last_wrong_at"] = last_wrong_map.get(wid, "")
            words.append(w)

    return {"words": words, "total": total, "page": page, "page_size": page_size}
