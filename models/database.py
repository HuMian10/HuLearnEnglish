"""Database models and operations for English Lesson app."""
import json
import aiosqlite
from datetime import datetime
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
                phonetic_uk TEXT DEFAULT '',
                phonetic_us TEXT DEFAULT '',
                audio_uk TEXT DEFAULT '',
                audio_us TEXT DEFAULT '',
                meanings TEXT DEFAULT '[]',
                category TEXT DEFAULT '',
                frequency_rank INTEGER DEFAULT 0,
                example_en TEXT DEFAULT '',
                example_cn TEXT DEFAULT '',
                plural TEXT DEFAULT '',
                past_tense TEXT DEFAULT '',
                past_participle TEXT DEFAULT '',
                present_participle TEXT DEFAULT '',
                comparative TEXT DEFAULT '',
                superlative TEXT DEFAULT '',
                third_person TEXT DEFAULT ''
            );

            CREATE TABLE IF NOT EXISTS learning_progress (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL REFERENCES users(id),
                word_id INTEGER NOT NULL REFERENCES words(id),
                status TEXT DEFAULT 'new' CHECK(status IN ('new','learning','mastered')),
                review_count INTEGER DEFAULT 0,
                correct_count INTEGER DEFAULT 0,
                streak INTEGER DEFAULT 0,
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
                review_ids TEXT DEFAULT '[]',
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

            CREATE TABLE IF NOT EXISTS word_books (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL UNIQUE,
                description TEXT DEFAULT '',
                icon TEXT DEFAULT '',
                word_count INTEGER DEFAULT 0,
                is_default INTEGER DEFAULT 0,
                created_at TEXT DEFAULT ''
            );

            CREATE TABLE IF NOT EXISTS word_book_words (
                word_book_id INTEGER NOT NULL REFERENCES word_books(id),
                word_id INTEGER NOT NULL REFERENCES words(id),
                PRIMARY KEY (word_book_id, word_id)
            );

            CREATE TABLE IF NOT EXISTS user_word_books (
                user_id INTEGER NOT NULL REFERENCES users(id),
                word_book_id INTEGER NOT NULL REFERENCES word_books(id),
                is_active INTEGER DEFAULT 1,
                activated_at TEXT DEFAULT '',
                PRIMARY KEY (user_id, word_book_id)
            );

            CREATE INDEX IF NOT EXISTS idx_words_category ON words(category);
            CREATE INDEX IF NOT EXISTS idx_words_frequency ON words(frequency_rank);
            CREATE INDEX IF NOT EXISTS idx_wbw_book ON word_book_words(word_book_id);
            CREATE INDEX IF NOT EXISTS idx_wbw_word ON word_book_words(word_id);
            CREATE INDEX IF NOT EXISTS idx_progress_user ON learning_progress(user_id);
            CREATE INDEX IF NOT EXISTS idx_progress_status ON learning_progress(user_id, status);
            CREATE INDEX IF NOT EXISTS idx_progress_next_review ON learning_progress(user_id, next_review);
            CREATE INDEX IF NOT EXISTS idx_plan_user ON daily_plan(user_id, date);

            CREATE TABLE IF NOT EXISTS wrong_words (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL REFERENCES users(id),
                word_id INTEGER NOT NULL REFERENCES words(id),
                wrong_count INTEGER DEFAULT 1,
                last_wrong_at TEXT DEFAULT '',
                UNIQUE(user_id, word_id)
            );

            CREATE TABLE IF NOT EXISTS favorite_words (
                user_id INTEGER NOT NULL REFERENCES users(id),
                word_id INTEGER NOT NULL REFERENCES words(id),
                created_at TEXT DEFAULT '',
                PRIMARY KEY (user_id, word_id)
            );

            CREATE TABLE IF NOT EXISTS user_streak (
                user_id INTEGER NOT NULL REFERENCES users(id) PRIMARY KEY,
                streak_days INTEGER DEFAULT 0,
                best_streak INTEGER DEFAULT 0,
                last_learn_date TEXT DEFAULT ''
            );

            CREATE INDEX IF NOT EXISTS idx_wrong_words_user ON wrong_words(user_id);
            CREATE INDEX IF NOT EXISTS idx_favorite_words_user ON favorite_words(user_id);
        
            CREATE TABLE IF NOT EXISTS news (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                source_id INTEGER NOT NULL,
                title TEXT NOT NULL,
                content TEXT DEFAULT '',
                photo_url TEXT DEFAULT '',
                source_time TEXT DEFAULT '',
                fetched_at TEXT DEFAULT '',
                UNIQUE(source_id)
            );
        
            CREATE INDEX IF NOT EXISTS idx_news_fetched ON news(fetched_at);

            CREATE TABLE IF NOT EXISTS user_news_read (
                user_id INTEGER NOT NULL REFERENCES users(id),
                news_id INTEGER NOT NULL REFERENCES news(id),
                read_at TEXT DEFAULT '',
                PRIMARY KEY (user_id, news_id)
            );

            CREATE INDEX IF NOT EXISTS idx_news_read_user ON user_news_read(user_id);
        """)

        await db.commit()

    # Migrate: add email column if missing
    async with aiosqlite.connect(db_path) as db:
        try:
            await db.execute("ALTER TABLE users ADD COLUMN email TEXT DEFAULT ''")
            await db.commit()
        except Exception:
            pass

    # Migrate: add new columns to words table for enhanced word info
    new_columns = [
        ("phonetic_uk", "TEXT DEFAULT ''"),
        ("phonetic_us", "TEXT DEFAULT ''"),
        ("audio_uk", "TEXT DEFAULT ''"),
        ("audio_us", "TEXT DEFAULT ''"),
        ("meanings", "TEXT DEFAULT '[]'"),
        ("plural", "TEXT DEFAULT ''"),
        ("past_tense", "TEXT DEFAULT ''"),
        ("past_participle", "TEXT DEFAULT ''"),
        ("present_participle", "TEXT DEFAULT ''"),
        ("comparative", "TEXT DEFAULT ''"),
        ("superlative", "TEXT DEFAULT ''"),
        ("third_person", "TEXT DEFAULT ''"),
    ]
    async with aiosqlite.connect(db_path) as db:
        for col_name, col_type in new_columns:
            try:
                await db.execute(f"ALTER TABLE words ADD COLUMN {col_name} {col_type}")
                await db.commit()
            except Exception:
                pass

    # Migrate: add streak column to learning_progress
    async with aiosqlite.connect(db_path) as db:
        try:
            await db.execute("ALTER TABLE learning_progress ADD COLUMN streak INTEGER DEFAULT 0")
            await db.commit()
        except Exception:
            pass

    # Migrate: convert old phonetic/pos/meaning_cn into new fields
    async with aiosqlite.connect(db_path) as db:
        # Copy old phonetic -> phonetic_us (as primary)
        try:
            await db.execute("UPDATE words SET phonetic_us = phonetic WHERE phonetic_us = '' AND phonetic != ''")
            await db.commit()
        except Exception:
            pass

        # Convert old pos + meaning_cn into meanings JSON
        cursor = await db.execute(
            "SELECT id, pos, meaning_cn FROM words WHERE (meanings = '' OR meanings = '[]') AND pos != '' AND meaning_cn != ''"
        )
        rows = await cursor.fetchall()
        for row in rows:
            meanings = json.dumps([{"pos": row[1], "meaning_cn": row[2]}])
            await db.execute("UPDATE words SET meanings = ? WHERE id = ?", (meanings, row[0]))
        await db.commit()

    # Migrate: seed default word book and link existing words
    async with aiosqlite.connect(db_path) as db:
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        await db.execute(
            """INSERT OR IGNORE INTO word_books (id, name, description, icon, is_default, created_at)
               VALUES (1, '日常生活', '涵盖日常饮食、出行、购物等高频词汇', '🏠', 1, ?)""",
            (now,)
        )
        await db.execute(
            """INSERT OR IGNORE INTO word_book_words (word_book_id, word_id)
               SELECT 1, id FROM words"""
        )
        await db.execute(
            "UPDATE word_books SET word_count = (SELECT COUNT(*) FROM word_book_words WHERE word_book_id = 1) WHERE id = 1"
        )
        await db.execute(
            """INSERT OR IGNORE INTO user_word_books (user_id, word_book_id, is_active, activated_at)
               SELECT id, 1, 1, ? FROM users""",
            (now,)
        )
        await db.commit()

    # Migrate: add default learning mode settings for existing users
    async with aiosqlite.connect(db_path) as db:
        mode_defaults = [
            ("recognize_mode", "direct"),
            ("learn_mode", "flip"),
            ("review_mode", "select_meaning"),
        ]
        cursor = await db.execute("SELECT id FROM users")
        rows = await cursor.fetchall()
        for row in rows:
            for key, value in mode_defaults:
                await db.execute(
                    "INSERT OR IGNORE INTO settings (user_id, key, value) VALUES (?, ?, ?)",
                    (row[0], key, value)
                )
        await db.commit()


async def close_db():
    global _db
    if _db:
        await _db.close()
        _db = None
