"""Database models and operations for English Lesson app."""
import aiosqlite
from config import DB_PATH

_db = None


async def get_db() -> aiosqlite.Connection:
    global _db
    if _db is None:
        _db = await aiosqlite.connect(DB_PATH)
        _db.row_factory = aiosqlite.Row
        await _db.execute("PRAGMA journal_mode=WAL")
        await _db.execute("PRAGMA foreign_keys=ON")
    return _db


async def init_database(db_path: str = DB_PATH):
    """Initialize database tables."""
    async with aiosqlite.connect(db_path) as db:
        await db.executescript("""
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                hashed_password TEXT NOT NULL,
                email TEXT DEFAULT '',
                created_at TEXT DEFAULT ''
            );

            CREATE TABLE IF NOT EXISTS words (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                word TEXT UNIQUE NOT NULL,
                phonetic TEXT DEFAULT '',
                pos TEXT DEFAULT '',
                meaning_cn TEXT DEFAULT '',
                category TEXT DEFAULT '',
                frequency_rank INTEGER DEFAULT 0,
                example_en TEXT DEFAULT '',
                example_cn TEXT DEFAULT ''
            );

            CREATE TABLE IF NOT EXISTS learning_progress (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL REFERENCES users(id),
                word_id INTEGER NOT NULL REFERENCES words(id),
                status TEXT DEFAULT 'new' CHECK(status IN ('new','learning','mastered')),
                review_count INTEGER DEFAULT 0,
                correct_count INTEGER DEFAULT 0,
                last_reviewed TEXT DEFAULT '',
                next_review TEXT DEFAULT '',
                created_at TEXT DEFAULT '',
                UNIQUE(user_id, word_id)
            );

            CREATE TABLE IF NOT EXISTS daily_plan (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL REFERENCES users(id),
                date TEXT NOT NULL,
                word_ids TEXT DEFAULT '[]',
                completed_ids TEXT DEFAULT '[]',
                total INTEGER DEFAULT 0,
                completed INTEGER DEFAULT 0,
                UNIQUE(user_id, date)
            );

            CREATE TABLE IF NOT EXISTS settings (
                user_id INTEGER NOT NULL REFERENCES users(id),
                key TEXT NOT NULL,
                value TEXT DEFAULT '',
                PRIMARY KEY (user_id, key)
            );

            CREATE INDEX IF NOT EXISTS idx_words_category ON words(category);
            CREATE INDEX IF NOT EXISTS idx_words_frequency ON words(frequency_rank);
            CREATE INDEX IF NOT EXISTS idx_progress_user ON learning_progress(user_id);
            CREATE INDEX IF NOT EXISTS idx_progress_status ON learning_progress(user_id, status);
            CREATE INDEX IF NOT EXISTS idx_progress_next_review ON learning_progress(user_id, next_review);
            CREATE INDEX IF NOT EXISTS idx_plan_user ON daily_plan(user_id, date);
        """)

        await db.commit()

    # Migrate: add email column if missing
    async with aiosqlite.connect(db_path) as db:
        try:
            await db.execute("ALTER TABLE users ADD COLUMN email TEXT DEFAULT ''")
            await db.commit()
        except Exception:
            pass  # Column already exists


async def close_db():
    global _db
    if _db:
        await _db.close()
        _db = None
