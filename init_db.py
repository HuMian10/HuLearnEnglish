"""Initialize database and import word data."""
import json
import sqlite3
import os

DB_PATH = os.getenv("DB_PATH", "english_lesson.db")
WORDS_JSON = os.path.join(os.path.dirname(__file__), "data", "words.json")


def create_tables(conn):
    conn.executescript("""
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


def import_words(conn):
    if not os.path.exists(WORDS_JSON):
        print(f"Words file not found: {WORDS_JSON}")
        print("Please generate words.json first by running: python generate_words.py")
        return

    with open(WORDS_JSON, "r", encoding="utf-8") as f:
        words = json.load(f)

    cur = conn.cursor()
    inserted = 0
    for w in words:
        try:
            cur.execute(
                """INSERT OR IGNORE INTO words
                (word, phonetic, pos, meaning_cn, category, frequency_rank, example_en, example_cn)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                (w["word"], w["phonetic"], w["pos"], w["meaning_cn"],
                 w["category"], w["frequency_rank"], w["example_en"], w["example_cn"])
            )
            if cur.rowcount > 0:
                inserted += 1
        except Exception as e:
            print(f"Error inserting {w['word']}: {e}")

    conn.commit()
    print(f"Imported {inserted} new words. Total words in DB: {cur.execute('SELECT COUNT(*) FROM words').fetchone()[0]}")


def main():
    if os.path.exists(DB_PATH):
        os.remove(DB_PATH)
        print(f"Removed old database: {DB_PATH}")

    conn = sqlite3.connect(DB_PATH)
    try:
        create_tables(conn)
        import_words(conn)
        print("Database initialized successfully!")
    finally:
        conn.close()


if __name__ == "__main__":
    main()
