"""Word service - business logic for word operations."""
import json
from models.database import get_db


def _parse_word(w: dict) -> dict:
    """Parse word dict, ensuring meanings is always a list."""
    if "meanings" in w and isinstance(w["meanings"], str):
        try:
            w["meanings"] = json.loads(w["meanings"])
        except (json.JSONDecodeError, TypeError):
            w["meanings"] = []
    if "meanings" not in w or not w["meanings"]:
        # Fallback: build from legacy pos/meaning_cn
        pos = w.get("pos", "")
        meaning = w.get("meaning_cn", "")
        w["meanings"] = [{"pos": pos, "meaning_cn": meaning}] if pos and meaning else []
    return w


async def get_words(category: str = "", search: str = "", page: int = 1, page_size: int = 50, word_book_id: int = 0):
    db = await get_db()

    if word_book_id:
        join = "JOIN word_book_words wbw ON words.id = wbw.word_id"
        conditions = ["wbw.word_book_id = ?"]
        params = [word_book_id]
        if category:
            conditions.append("words.category = ?")
            params.append(category)
        if search:
            conditions.append("(words.word LIKE ? OR words.meaning_cn LIKE ?)")
            params.extend([f"%{search}%", f"%{search}%"])
        where = f"WHERE {' AND '.join(conditions)}"
    else:
        join = ""
        conditions = []
        params = []
        if category:
            conditions.append("category = ?")
            params.append(category)
        if search:
            conditions.append("(word LIKE ? OR meaning_cn LIKE ?)")
            params.extend([f"%{search}%", f"%{search}%"])
        where = f"WHERE {' AND '.join(conditions)}" if conditions else ""

    count_row = await db.execute(f"SELECT COUNT(DISTINCT words.id) FROM words {join} {where}", params)
    total = (await count_row.fetchone())[0]

    offset = (page - 1) * page_size
    cursor = await db.execute(
        f"SELECT DISTINCT words.* FROM words {join} {where} ORDER BY words.frequency_rank LIMIT ? OFFSET ?",
        params + [page_size, offset]
    )
    rows = await cursor.fetchall()

    words = [_parse_word(dict(row)) for row in rows]
    return {"words": words, "total": total, "page": page, "page_size": page_size}


async def get_word(word_id: int):
    db = await get_db()
    cursor = await db.execute("SELECT * FROM words WHERE id = ?", (word_id,))
    row = await cursor.fetchone()
    return _parse_word(dict(row)) if row else None


async def get_categories(word_book_id: int = 0):
    db = await get_db()
    if word_book_id:
        cursor = await db.execute(
            """SELECT words.category, COUNT(*) as count FROM words
               JOIN word_book_words wbw ON words.id = wbw.word_id
               WHERE wbw.word_book_id = ?
               GROUP BY words.category ORDER BY words.category""",
            (word_book_id,)
        )
    else:
        cursor = await db.execute(
            "SELECT category, COUNT(*) as count FROM words GROUP BY category ORDER BY category"
        )
    rows = await cursor.fetchall()
    return [{"category": row[0], "count": row[1]} for row in rows]


async def get_word_count(word_book_id: int = 0):
    db = await get_db()
    if word_book_id:
        cursor = await db.execute(
            "SELECT COUNT(DISTINCT word_id) FROM word_book_words WHERE word_book_id = ?",
            (word_book_id,)
        )
    else:
        cursor = await db.execute("SELECT COUNT(*) FROM words")
    return (await cursor.fetchone())[0]


async def get_distractors(word_id: int, count: int = 3) -> list[dict]:
    """Get distractor words for quiz options. Prefers same category, excludes the given word."""
    db = await get_db()
    # First try same category
    cursor = await db.execute(
        "SELECT id, word, meaning_cn, category FROM words WHERE id != ? AND category = (SELECT category FROM words WHERE id = ?) ORDER BY RANDOM() LIMIT ?",
        (word_id, word_id, count)
    )
    rows = await cursor.fetchall()
    distractors = [_parse_word(dict(row)) for row in rows]

    # Fill remaining from any category
    if len(distractors) < count:
        exclude_ids = [word_id] + [d["id"] for d in distractors]
        placeholders = ",".join("?" * len(exclude_ids))
        cursor = await db.execute(
            f"SELECT id, word, meaning_cn, category FROM words WHERE id NOT IN ({placeholders}) ORDER BY RANDOM() LIMIT ?",
            exclude_ids + [count - len(distractors)]
        )
        rows = await cursor.fetchall()
        distractors.extend([_parse_word(dict(row)) for row in rows])

    return distractors
