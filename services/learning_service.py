"""Learning service - business logic for learning plans and progress."""
import json
from datetime import datetime, timedelta
from models.database import get_db


# Ebbinghaus intervals: 1h, 1d, 2d, 4d, 7d, 15d, 30d
REVIEW_INTERVALS = [0, 1, 2, 4, 7, 15, 30]


def _next_review_date(review_count: int, last_reviewed: str) -> str:
    """Calculate next review date based on Ebbinghaus forgetting curve."""
    idx = min(review_count, len(REVIEW_INTERVALS) - 1)
    days = REVIEW_INTERVALS[idx]
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


async def generate_daily_plan(user_id: int):
    """Generate today's learning plan with new words and due reviews."""
    db = await get_db()
    today = datetime.now().strftime("%Y-%m-%d")

    # Check if plan already exists for today
    cursor = await db.execute(
        "SELECT * FROM daily_plan WHERE user_id = ? AND date = ?", (user_id, today)
    )
    existing = await cursor.fetchone()
    if existing:
        return dict(existing)

    # Get daily words count setting
    cursor = await db.execute(
        "SELECT value FROM settings WHERE user_id = ? AND key = 'daily_words'", (user_id,)
    )
    row = await cursor.fetchone()
    daily_count = int(row[0]) if row else 10

    # Get words due for review
    cursor = await db.execute(
        """SELECT word_id FROM learning_progress
           WHERE user_id = ? AND status IN ('learning', 'new')
           AND next_review <= ? AND next_review != ''
           ORDER BY next_review""",
        (user_id, today)
    )
    review_rows = await cursor.fetchall()
    review_ids = [r[0] for r in review_rows]

    # Get new words (not yet in this user's learning_progress)
    new_count = max(0, daily_count - len(review_ids))
    if new_count > 0:
        cursor = await db.execute(
            """SELECT id FROM words
               WHERE id NOT IN (SELECT word_id FROM learning_progress WHERE user_id = ?)
               ORDER BY frequency_rank
               LIMIT ?""",
            (user_id, new_count)
        )
        new_rows = await cursor.fetchall()
        new_ids = [r[0] for r in new_rows]
    else:
        new_ids = []

    all_ids = review_ids + new_ids
    if not all_ids:
        return None

    # Create plan
    await db.execute(
        """INSERT INTO daily_plan (user_id, date, word_ids, completed_ids, total, completed)
           VALUES (?, ?, ?, '[]', ?, 0)""",
        (user_id, today, json.dumps(all_ids), len(all_ids))
    )

    # Initialize learning_progress for new words
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    for word_id in new_ids:
        await db.execute(
            """INSERT OR IGNORE INTO learning_progress
               (user_id, word_id, status, review_count, correct_count, last_reviewed, next_review, created_at)
               VALUES (?, ?, 'new', 0, 0, '', ?, ?)""",
            (user_id, word_id, today, now)
        )

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
    """Submit a review result for a word."""
    db = await get_db()
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    today = datetime.now().strftime("%Y-%m-%d")

    cursor = await db.execute(
        "SELECT * FROM learning_progress WHERE user_id = ? AND word_id = ?", (user_id, word_id)
    )
    progress = await cursor.fetchone()

    if not progress:
        await db.execute(
            """INSERT INTO learning_progress
               (user_id, word_id, status, review_count, correct_count, last_reviewed, next_review, created_at)
               VALUES (?, ?, ?, 1, ?, ?, ?, ?)""",
            (user_id, word_id, "learning", 1 if correct else 0, now, _next_review_date(1, now), now)
        )
    else:
        p = dict(progress)
        new_review_count = p["review_count"] + 1
        new_correct_count = p["correct_count"] + (1 if correct else 0)

        if new_review_count >= 5 and new_correct_count / new_review_count >= 0.8:
            new_status = "mastered"
        elif new_review_count >= 1:
            new_status = "learning"
        else:
            new_status = "new"

        next_review = _next_review_date(new_review_count, now)

        await db.execute(
            """UPDATE learning_progress
               SET status=?, review_count=?, correct_count=?, last_reviewed=?, next_review=?
               WHERE user_id=? AND word_id=?""",
            (new_status, new_review_count, new_correct_count, now, next_review, user_id, word_id)
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

    total_words = (await (await db.execute("SELECT COUNT(*) FROM words")).fetchone())[0]
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
            w = dict(row)
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
        cursor = await db.execute("SELECT id, word, meaning_cn, pos FROM words WHERE id = ?", (wid,))
        row = await cursor.fetchone()
        if row:
            words.append({
                "id": row[0],
                "word": row[1],
                "meaning_cn": row[2],
                "pos": row[3],
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

    # Reset completed state
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
