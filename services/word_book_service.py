"""Word book service - business logic for word book management."""
from datetime import datetime
from models.database import get_db


async def get_all_word_books() -> list[dict]:
    db = await get_db()
    cursor = await db.execute("SELECT * FROM word_books ORDER BY is_default DESC, id")
    rows = await cursor.fetchall()
    return [dict(row) for row in rows]


async def get_user_active_books(user_id: int) -> list[dict]:
    db = await get_db()
    cursor = await db.execute(
        """SELECT wb.* FROM word_books wb
           JOIN user_word_books uwb ON wb.id = uwb.word_book_id
           WHERE uwb.user_id = ? AND uwb.is_active = 1
           ORDER BY wb.is_default DESC, wb.id""",
        (user_id,)
    )
    rows = await cursor.fetchall()
    return [dict(row) for row in rows]


async def get_active_book_ids(user_id: int) -> list[int]:
    books = await get_user_active_books(user_id)
    return [b["id"] for b in books]


async def activate_book(user_id: int, book_id: int):
    """Activate a word book, deactivating all others (only one active at a time)."""
    db = await get_db()
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # Deactivate all current books
    await db.execute(
        "UPDATE user_word_books SET is_active = 0, updated_at = ? WHERE user_id = ?",
        (now, user_id)
    )

    # Activate the target book
    await db.execute(
        """INSERT INTO user_word_books (user_id, word_book_id, is_active, activated_at, created_at, updated_at)
           VALUES (?, ?, 1, ?, ?, ?)
           ON CONFLICT(user_id, word_book_id) DO UPDATE SET is_active=1, activated_at=?, updated_at=?""",
        (user_id, book_id, now, now, now, now, now)
    )

    # Clear today's plan so it regenerates with the new book's words
    today = datetime.now().strftime("%Y-%m-%d")
    await db.execute(
        "DELETE FROM daily_plan WHERE user_id = ? AND date = ?",
        (user_id, today)
    )

    await db.commit()


async def deactivate_book(user_id: int, book_id: int):
    db = await get_db()
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    # Prevent deactivating the default book
    cursor = await db.execute("SELECT is_default FROM word_books WHERE id = ?", (book_id,))
    row = await cursor.fetchone()
    if row and row[0]:
        return False
    await db.execute(
        "UPDATE user_word_books SET is_active = 0, updated_at = ? WHERE user_id = ? AND word_book_id = ?",
        (now, user_id, book_id)
    )
    await db.commit()
    return True
