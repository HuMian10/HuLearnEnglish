"""News fetching and storage service."""
import requests
from datetime import datetime, timedelta
from bs4 import BeautifulSoup
import re
from models.database import get_db
from config import NEWS_FETCH_COUNT, NEWS_RETENTION_DAYS, NEWS_LIST_DAYS, NEWS_LIST_LIMIT, NEWS_SOURCE_URL, NEWS_API_URL


def extract_snumber_from_url(base_url: str) -> int | None:
    """Get the first article ID from aibase news page."""
    try:
        response = requests.get(base_url, timeout=15)
        response.encoding = 'utf-8'
        soup = BeautifulSoup(response.text, 'html.parser')
        index = str(soup).find('initialArticles')
        text = str(soup)[index: index + 50]
        pattern = r'\\"Id\\":(\d+)'
        match = re.search(pattern, text)
        if match:
            return int(match.group(1))
        else:
            print("[news] No ID found on page")
            return None
    except Exception as e:
        print(f"[news] extract_snumber error: {e}")
        return None


def extract_news(snumber: int) -> dict | None:
    """Fetch a single news article from aibase API."""
    url = NEWS_API_URL
    params = {
        't': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        'langType': 'en',
        'id': snumber,
        'type': 'news',
    }
    try:
        response = requests.get(url, params=params, timeout=15)
        result = response.json()
        title = result['data']['title']
        photo_url = result['data']['thumb']
        content = result['data']['summary']
        create_time = result['data']['createTime']
        return {
            'source_id': snumber,
            'title': title,
            'content': content,
            'photo_url': photo_url,
            'source_time': create_time,
        }
    except Exception as e:
        print(f"[news] extract_news({snumber}) error: {e}")
        return None


async def fetch_and_store_news() -> int:
    """Fetch latest 20 news articles and store them in DB. Returns count of new articles."""
    snumber = extract_snumber_from_url(NEWS_SOURCE_URL)
    if not snumber:
        return 0

    articles = []
    for id in range(snumber - NEWS_FETCH_COUNT, snumber):
        article = extract_news(id)
        if article:
            articles.append(article)

    db = await get_db()
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    count = 0
    for article in articles:
        try:
            await db.execute(
                """INSERT OR IGNORE INTO news (source_id, title, content, photo_url, source_time, fetched_at, created_at, updated_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                (article['source_id'], article['title'], article['content'],
                 article['photo_url'], article['source_time'], now, now, now)
            )
            count += 1
        except Exception as e:
            print(f"[news] store error: {e}")
    await db.commit()

    # Delete news older than 7 days
    cutoff = (datetime.now() - timedelta(days=NEWS_RETENTION_DAYS)).strftime("%Y-%m-%d")
    await db.execute("DELETE FROM news WHERE fetched_at < ?", (cutoff,))
    await db.commit()

    print(f"[news] Stored {count} new articles")
    return count


async def get_news_list(days: int = NEWS_LIST_DAYS, user_id: int = 0, date: str = "") -> list:
    """Get recent news articles from DB, with optional date filter and read status."""
    db = await get_db()

    if date:
        # Filter by specific date
        where = "WHERE fetched_at >= ? AND fetched_at < ?"
        next_day = (datetime.strptime(date, '%Y-%m-%d') + timedelta(days=1)).strftime('%Y-%m-%d')
        params = [date, next_day]
    else:
        cutoff = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")
        where = "WHERE fetched_at >= ?"
        params = [cutoff]

    cursor = await db.execute(
        f"""SELECT id, source_id, title, content, photo_url, source_time, fetched_at
           FROM news {where}
           ORDER BY source_time DESC LIMIT {NEWS_LIST_LIMIT}""",
        params
    )
    rows = await cursor.fetchall()

    # Get read status for this user
    read_ids = set()
    if user_id:
        news_ids = [row[0] for row in rows]
        if news_ids:
            placeholders = ','.join('?' * len(news_ids))
            read_cursor = await db.execute(
                f"SELECT news_id FROM user_news_read WHERE user_id = ? AND news_id IN ({placeholders})",
                [user_id] + news_ids
            )
            read_rows = await read_cursor.fetchall()
            read_ids = {r[0] for r in read_rows}

    return [
        {
            'id': row[0],
            'source_id': row[1],
            'title': row[2],
            'content': row[3],
            'photo_url': row[4],
            'source_time': row[5],
            'fetched_at': row[6],
            'is_read': row[0] in read_ids,
        }
        for row in rows
    ]


async def has_fetched_today() -> bool:
    """Check if news has already been fetched today."""
    db = await get_db()
    today = datetime.now().strftime("%Y-%m-%d")
    cursor = await db.execute(
        "SELECT COUNT(*) FROM news WHERE fetched_at >= ?",
        (today,)
    )
    row = await cursor.fetchone()
    return row[0] > 0


async def get_news_detail(news_id: int) -> dict | None:
    """Get a single news article by database ID."""
    db = await get_db()
    cursor = await db.execute(
        """SELECT id, source_id, title, content, photo_url, source_time, fetched_at
           FROM news WHERE id = ?""",
        (news_id,)
    )
    row = await cursor.fetchone()
    if not row:
        return None
    return {
        'id': row[0],
        'source_id': row[1],
        'title': row[2],
        'content': row[3],
        'photo_url': row[4],
        'source_time': row[5],
        'fetched_at': row[6],
    }


async def mark_news_read(user_id: int, news_id: int):
    """Mark a news article as read for a user."""
    db = await get_db()
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    await db.execute(
        "INSERT OR IGNORE INTO user_news_read (user_id, news_id, read_at, created_at) VALUES (?, ?, ?, ?)",
        (user_id, news_id, now, now)
    )
    await db.commit()


async def get_available_dates(days: int = NEWS_RETENTION_DAYS) -> list:
    """Get list of dates that have news articles."""
    db = await get_db()
    cutoff = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")
    cursor = await db.execute(
        """SELECT DISTINCT DATE(fetched_at) as date, COUNT(*) as count
           FROM news WHERE fetched_at >= ?
           GROUP BY DATE(fetched_at)
           ORDER BY date DESC""",
        (cutoff,)
    )
    rows = await cursor.fetchall()
    return [{"date": row[0], "count": row[1]} for row in rows]