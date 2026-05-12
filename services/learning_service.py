"""Learning service - business logic for learning plans and progress."""
import json
from datetime import datetime, timedelta
from models.database import get_db
from services.word_book_service import get_active_book_ids
from services.word_service import _parse_word


# SM-2 inspired intervals based on streak (consecutive correct answers)
# streak 0: just failed, review again soon
# streak 1: got it right once, review tomorrow
# streak 2: 3 days
# streak 3: 7 days
# streak 4: 14 days
# streak 5: 30 days
# streak 6+: 60 days
STREAK_INTERVALS = [1, 1, 3, 7, 14, 30, 60]


def _next_review_date(streak: int, correct: bool, last_reviewed: str) -> str:
    """Calculate next review date based on SM-2 inspired algorithm.

    streak: consecutive correct answers
    correct: whether this review was correct
    """
    if correct:
        idx = min(streak, len(STREAK_INTERVALS) - 1)
        days = STREAK_INTERVALS[idx]
    else:
        # Failed: review again tomorrow
        days = 1

    base = datetime.fromisoformat(last_reviewed) if last_reviewed else datetime.now()
    return (base + timedelta(days=days)).strftime("%Y-%m-%d")


async def get_settings(user_id: int):
    db = await get_db()
    cursor = await db.execute("SELECT key, value FROM settings WHERE user_id = ?", (user_id,))
    rows = await cursor.fetchall()
    return {row[0]: row[1] for row in rows}


async def update_setting(user_id: int, key: str, value: str):
    db = await get_db()
    await db.execute(
        """INSERT INTO settings (user_id, key, value) VALUES (?, ?, ?)
           ON CONFLICT(user_id, key) DO UPDATE SET value=?""",
        (user_id, key, value, value)
    )
    await db.commit()


async def _fetch_new_words(user_id: int, count: int) -> list[int]:
    """Fetch new word IDs not yet in user's learning_progress."""
    active_book_ids = await get_active_book_ids(user_id)
    if not active_book_ids or count <= 0:
        return []
    db = await get_db()
    placeholders = ",".join("?" * len(active_book_ids))
    cursor = await db.execute(
        f"""SELECT DISTINCT w.id FROM words w
           JOIN word_book_words wbw ON w.id = wbw.word_id
           WHERE w.id NOT IN (SELECT word_id FROM learning_progress WHERE user_id = ?)
           AND wbw.word_book_id IN ({placeholders})
           ORDER BY w.frequency_rank
           LIMIT ?""",
        (user_id, *active_book_ids, count)
    )
    return [r[0] for r in await cursor.fetchall()]


async def _fetch_review_words(user_id: int) -> list[int]:
    """Fetch word IDs due for review today."""
    db = await get_db()
    today = datetime.now().strftime("%Y-%m-%d")
    active_book_ids = await get_active_book_ids(user_id)
    if not active_book_ids:
        return []
    placeholders = ",".join("?" * len(active_book_ids))
    cursor = await db.execute(
        f"""SELECT DISTINCT lp.word_id FROM learning_progress lp
           JOIN word_book_words wbw ON lp.word_id = wbw.word_id
           WHERE lp.user_id = ? AND lp.status IN ('learning', 'new')
           AND lp.next_review <= ? AND lp.next_review != ''
           AND wbw.word_book_id IN ({placeholders})
           ORDER BY lp.next_review""",
        (user_id, today, *active_book_ids)
    )
    return [r[0] for r in await cursor.fetchall()]


async def _init_new_word_progress(db, user_id: int, word_ids: list[int], today: str):
    """Insert learning_progress rows for new words."""
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    for word_id in word_ids:
        await db.execute(
            """INSERT OR IGNORE INTO learning_progress
               (user_id, word_id, status, review_count, correct_count, streak, last_reviewed, next_review, created_at)
               VALUES (?, ?, 'new', 0, 0, 0, '', ?, ?)""",
            (user_id, word_id, today, now)
        )


async def generate_daily_plan(user_id: int):
    """Generate today's learning plan with new words and due reviews.

    daily_count setting controls NEW words per day only.
    Due reviews are added on top, not competing for new word slots.
    """
    db = await get_db()
    today = datetime.now().strftime("%Y-%m-%d")

    # Check if plan already exists for today
    cursor = await db.execute(
        "SELECT * FROM daily_plan WHERE user_id = ? AND date = ?", (user_id, today)
    )
    existing = await cursor.fetchone()
    if existing:
        return dict(existing)

    # Get daily new words count setting
    cursor = await db.execute(
        "SELECT value FROM settings WHERE user_id = ? AND key = 'daily_words'", (user_id,)
    )
    row = await cursor.fetchone()
    daily_new_count = int(row[0]) if row else 10

    review_ids = await _fetch_review_words(user_id)
    new_ids = await _fetch_new_words(user_id, daily_new_count)

    all_ids = review_ids + new_ids
    if not all_ids:
        return None

    # Create plan
    await db.execute(
        """INSERT INTO daily_plan (user_id, date, word_ids, review_ids, completed_ids, total, completed)
           VALUES (?, ?, ?, ?, '[]', ?, 0)""",
        (user_id, today, json.dumps(all_ids), json.dumps(review_ids), len(all_ids))
    )

    await _init_new_word_progress(db, user_id, new_ids, today)
    await db.commit()

    cursor = await db.execute(
        "SELECT * FROM daily_plan WHERE user_id = ? AND date = ?", (user_id, today)
    )
    return dict(await cursor.fetchone())


async def continue_plan(user_id: int):
    """Append a new batch of words to today's plan for continued learning."""
    db = await get_db()
    today = datetime.now().strftime("%Y-%m-%d")

    cursor = await db.execute(
        "SELECT * FROM daily_plan WHERE user_id = ? AND date = ?", (user_id, today)
    )
    plan = await cursor.fetchone()
    if not plan:
        # No plan yet, generate one
        return await generate_daily_plan(user_id)

    p = dict(plan)
    existing_ids = set(json.loads(p["word_ids"]))

    # Get daily batch size
    cursor = await db.execute(
        "SELECT value FROM settings WHERE user_id = ? AND key = 'daily_words'", (user_id,)
    )
    row = await cursor.fetchone()
    batch_size = int(row[0]) if row else 10

    new_ids = await _fetch_new_words(user_id, batch_size)
    # Filter out words already in today's plan
    new_ids = [wid for wid in new_ids if wid not in existing_ids]

    if not new_ids:
        return None

    # Append to existing plan
    all_ids = json.loads(p["word_ids"]) + new_ids
    await db.execute(
        "UPDATE daily_plan SET word_ids=?, total=? WHERE user_id=? AND date=?",
        (json.dumps(all_ids), len(all_ids), user_id, today)
    )

    await _init_new_word_progress(db, user_id, new_ids, today)
    await db.commit()

    cursor = await db.execute(
        "SELECT * FROM daily_plan WHERE user_id = ? AND date = ?", (user_id, today)
    )
    return dict(await cursor.fetchone())


async def get_today_plan(user_id: int):
    """Get today's learning plan."""
    db = await get_db()
    today = datetime.now().strftime("%Y-%m-%d")
    cursor = await db.execute(
        "SELECT * FROM daily_plan WHERE user_id = ? AND date = ?", (user_id, today)
    )
    row = await cursor.fetchone()
    return dict(row) if row else None


async def submit_review(user_id: int, word_id: int, correct: bool):
    """Submit a review result for a word. Uses SM-2 inspired algorithm."""
    db = await get_db()
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    today = datetime.now().strftime("%Y-%m-%d")

    cursor = await db.execute(
        "SELECT * FROM learning_progress WHERE user_id = ? AND word_id = ?", (user_id, word_id)
    )
    progress = await cursor.fetchone()

    if not progress:
        streak = 1 if correct else 0
        next_review = _next_review_date(streak, correct, now)
        await db.execute(
            """INSERT INTO learning_progress
               (user_id, word_id, status, review_count, correct_count, streak, last_reviewed, next_review, created_at)
               VALUES (?, ?, 'learning', 1, ?, ?, ?, ?, ?)""",
            (user_id, word_id, 1 if correct else 0, streak, now, next_review, now)
        )
    else:
        p = dict(progress)
        new_review_count = p["review_count"] + 1
        new_correct_count = p["correct_count"] + (1 if correct else 0)

        # Update streak: increment on correct, reset to 0 on incorrect
        old_streak = p.get("streak", 0) or 0
        new_streak = old_streak + 1 if correct else 0

        if new_review_count >= 5 and new_correct_count / new_review_count >= 0.8:
            new_status = "mastered"
        elif new_review_count >= 1:
            new_status = "learning"
        else:
            new_status = "new"

        next_review = _next_review_date(new_streak, correct, now)

        await db.execute(
            """UPDATE learning_progress
               SET status=?, review_count=?, correct_count=?, streak=?, last_reviewed=?, next_review=?
               WHERE user_id=? AND word_id=?""",
            (new_status, new_review_count, new_correct_count, new_streak, now, next_review, user_id, word_id)
        )

    # Update daily plan completed count
    cursor = await db.execute(
        "SELECT * FROM daily_plan WHERE user_id = ? AND date = ?", (user_id, today)
    )
    plan = await cursor.fetchone()
    if plan:
        p = dict(plan)
        completed_ids = json.loads(p["completed_ids"])
        if word_id not in completed_ids:
            completed_ids.append(word_id)
            await db.execute(
                "UPDATE daily_plan SET completed_ids=?, completed=? WHERE user_id=? AND date=?",
                (json.dumps(completed_ids), len(completed_ids), user_id, today)
            )

    await db.commit()


async def get_learning_stats(user_id: int):
    """Get overall learning statistics for a user."""
    db = await get_db()

    active_book_ids = await get_active_book_ids(user_id)
    if active_book_ids:
        placeholders = ",".join("?" * len(active_book_ids))
        total_words = (await (await db.execute(
            f"SELECT COUNT(DISTINCT word_id) FROM word_book_words WHERE word_book_id IN ({placeholders})",
            active_book_ids
        )).fetchone())[0]
    else:
        total_words = 0
    new_count = (await (await db.execute(
        "SELECT COUNT(*) FROM learning_progress WHERE user_id=? AND status='new'", (user_id,)
    )).fetchone())[0]
    learning_count = (await (await db.execute(
        "SELECT COUNT(*) FROM learning_progress WHERE user_id=? AND status='learning'", (user_id,)
    )).fetchone())[0]
    mastered_count = (await (await db.execute(
        "SELECT COUNT(*) FROM learning_progress WHERE user_id=? AND status='mastered'", (user_id,)
    )).fetchone())[0]

    today = datetime.now().strftime("%Y-%m-%d")
    due_review = (await (await db.execute(
        """SELECT COUNT(*) FROM learning_progress
           WHERE user_id=? AND status IN ('new','learning') AND next_review <= ? AND next_review != ''""",
        (user_id, today)
    )).fetchone())[0]

    cursor = await db.execute(
        "SELECT * FROM daily_plan WHERE user_id = ? AND date = ?", (user_id, today)
    )
    plan = await cursor.fetchone()
    today_total = 0
    today_completed = 0
    if plan:
        p = dict(plan)
        today_total = p["total"]
        today_completed = p["completed"]

    return {
        "total_words": total_words,
        "new_count": new_count,
        "learning_count": learning_count,
        "mastered_count": mastered_count,
        "due_review": due_review,
        "today_total": today_total,
        "today_completed": today_completed,
        "unlearned": total_words - new_count - learning_count - mastered_count,
    }


async def get_plan_words(user_id: int):
    """Get words for today's plan with their details."""
    db = await get_db()
    today = datetime.now().strftime("%Y-%m-%d")
    cursor = await db.execute(
        "SELECT * FROM daily_plan WHERE user_id = ? AND date = ?", (user_id, today)
    )
    plan = await cursor.fetchone()

    if not plan:
        return [], []

    p = dict(plan)
    word_ids = json.loads(p["word_ids"])
    completed_ids = json.loads(p["completed_ids"])

    words = []
    remaining = []
    for wid in word_ids:
        cursor = await db.execute("SELECT * FROM words WHERE id = ?", (wid,))
        row = await cursor.fetchone()
        if row:
            w = _parse_word(dict(row))
            w["completed"] = wid in completed_ids
            words.append(w)
            if wid not in completed_ids:
                remaining.append(w)

    return words, remaining


async def get_calendar_month(user_id: int, year: int, month: int):
    """Get daily summary for a given month."""
    db = await get_db()
    prefix = f"{year:04d}-{month:02d}"
    cursor = await db.execute(
        "SELECT date, total, completed FROM daily_plan WHERE user_id = ? AND date LIKE ?",
        (user_id, prefix + "%"),
    )
    rows = await cursor.fetchall()
    days = {}
    for row in rows:
        days[row[0]] = {"total": row[1], "completed": row[2]}
    return {"year": year, "month": month, "days": days}


async def get_day_detail(user_id: int, date: str):
    """Get detail for a specific day."""
    db = await get_db()
    cursor = await db.execute(
        "SELECT * FROM daily_plan WHERE user_id = ? AND date = ?", (user_id, date)
    )
    plan = await cursor.fetchone()

    if not plan:
        return {"date": date, "total": 0, "completed": 0, "words": [], "reviewed_count": 0}

    p = dict(plan)
    word_ids = json.loads(p["word_ids"])
    completed_ids = json.loads(p["completed_ids"])

    words = []
    for wid in word_ids:
        cursor = await db.execute("SELECT * FROM words WHERE id = ?", (wid,))
        row = await cursor.fetchone()
        if row:
            w = dict(row)
            meanings = []
            if w.get("meanings"):
                try:
                    meanings = json.loads(w["meanings"]) if isinstance(w["meanings"], str) else w["meanings"]
                except (json.JSONDecodeError, TypeError):
                    pass
            if not meanings and w.get("pos") and w.get("meaning_cn"):
                meanings = [{"pos": w["pos"], "meaning_cn": w["meaning_cn"]}]
            primary = meanings[0] if meanings else {}
            words.append({
                "id": w["id"],
                "word": w["word"],
                "meaning_cn": primary.get("meaning_cn", w.get("meaning_cn", "")),
                "pos": primary.get("pos", w.get("pos", "")),
                "meanings": meanings,
                "completed": wid in completed_ids,
            })

    # Count words reviewed on this day
    cursor = await db.execute(
        """SELECT COUNT(*) FROM learning_progress
           WHERE user_id = ? AND last_reviewed LIKE ?""",
        (user_id, date + "%"),
    )
    reviewed_count = (await cursor.fetchone())[0]

    return {
        "date": date,
        "total": p["total"],
        "completed": p["completed"],
        "words": words,
        "reviewed_count": reviewed_count,
    }


async def clear_day_progress(user_id: int, date: str):
    """Clear completed progress for a specific day, allowing re-learning."""
    db = await get_db()
    cursor = await db.execute(
        "SELECT * FROM daily_plan WHERE user_id = ? AND date = ?", (user_id, date)
    )
    plan = await cursor.fetchone()
    if not plan:
        return

    await db.execute(
        "UPDATE daily_plan SET completed_ids = '[]', completed = 0 WHERE user_id = ? AND date = ?",
        (user_id, date),
    )
    await db.commit()


async def clear_all_plans(user_id: int):
    """Delete all daily plans for a user."""
    db = await get_db()
    await db.execute("DELETE FROM daily_plan WHERE user_id = ?", (user_id,))
    await db.commit()


async def get_due_review_words(user_id: int):
    """Get words that are due for review today, separate from new learning."""
    db = await get_db()
    today = datetime.now().strftime("%Y-%m-%d")

    active_book_ids = await get_active_book_ids(user_id)
    if not active_book_ids:
        return []

    placeholders = ",".join("?" * len(active_book_ids))
    cursor = await db.execute(
        f"""SELECT DISTINCT lp.word_id FROM learning_progress lp
           JOIN word_book_words wbw ON lp.word_id = wbw.word_id
           WHERE lp.user_id = ? AND lp.status IN ('learning', 'new')
           AND lp.next_review <= ? AND lp.next_review != ''
           AND wbw.word_book_id IN ({placeholders})
           ORDER BY lp.next_review""",
        (user_id, today, *active_book_ids)
    )
    review_rows = await cursor.fetchall()
    review_ids = [r[0] for r in review_rows]

    if not review_ids:
        return []

    words = []
    for wid in review_ids:
        cursor = await db.execute("SELECT * FROM words WHERE id = ?", (wid,))
        row = await cursor.fetchone()
        if row:
            words.append(_parse_word(dict(row)))
    return words
