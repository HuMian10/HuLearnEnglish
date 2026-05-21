"""Streak service - track consecutive learning days."""
from datetime import datetime, timedelta
from models.database import get_db


async def update_streak(user_id: int):
    """Update streak for a user when they complete a learning activity.

    Called after submit_review or mark_word_mastered.
    """
    db = await get_db()
    today = datetime.now().strftime("%Y-%m-%d")

    cursor = await db.execute(
        "SELECT streak_days, best_streak, last_learn_date FROM user_streak WHERE user_id = ?",
        (user_id,)
    )
    row = await cursor.fetchone()

    if not row:
        # First time learning
        await db.execute(
            "INSERT INTO user_streak (user_id, streak_days, best_streak, last_learn_date) VALUES (?, 1, 1, ?)",
            (user_id, today)
        )
        await db.commit()
        return 1

    streak_days, best_streak, last_learn_date = row

    if last_learn_date == today:
        # Already updated today
        return streak_days

    yesterday = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")
    if last_learn_date == yesterday:
        # Continued streak
        streak_days += 1
    else:
        # Streak broken
        streak_days = 1

    best_streak = max(best_streak, streak_days)

    await db.execute(
        "UPDATE user_streak SET streak_days = ?, best_streak = ?, last_learn_date = ? WHERE user_id = ?",
        (streak_days, best_streak, today, user_id)
    )
    await db.commit()
    return streak_days


async def get_streak(user_id: int) -> dict:
    """Get streak info for a user."""
    db = await get_db()
    cursor = await db.execute(
        "SELECT streak_days, best_streak, last_learn_date FROM user_streak WHERE user_id = ?",
        (user_id,)
    )
    row = await cursor.fetchone()

    if not row:
        return {"streak_days": 0, "best_streak": 0, "last_learn_date": ""}

    streak_days, best_streak, last_learn_date = row

    # Check if streak is still active (not broken)
    today = datetime.now().strftime("%Y-%m-%d")
    yesterday = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")
    if last_learn_date != today and last_learn_date != yesterday:
        # Streak was broken since last check
        if streak_days > 0:
            streak_days = 0
            await db.execute(
                "UPDATE user_streak SET streak_days = 0 WHERE user_id = ?",
                (user_id,)
            )
            await db.commit()

    return {"streak_days": streak_days, "best_streak": best_streak, "last_learn_date": last_learn_date}
