"""Authentication service - user registration, login, JWT."""
from datetime import datetime, timedelta
from jose import JWTError, jwt
import bcrypt

from config import SECRET_KEY, ALGORITHM, ACCESS_TOKEN_EXPIRE_MINUTES
from models.database import get_db


def get_password_hash(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return bcrypt.checkpw(plain_password.encode("utf-8"), hashed_password.encode("utf-8"))


def create_access_token(user_id: int) -> str:
    expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    payload = {"sub": str(user_id), "exp": expire}
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)


def decode_token(token: str) -> int | None:
    """Decode JWT token, return user_id or None."""
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id = int(payload.get("sub", 0))
        return user_id if user_id > 0 else None
    except (JWTError, ValueError):
        return None


async def register(username: str, password: str, email: str = "") -> dict:
    """Register a new user. Returns {ok: True, user_id} or {ok: False, error}."""
    db = await get_db()

    cursor = await db.execute("SELECT id FROM users WHERE username = ?", (username,))
    if await cursor.fetchone():
        return {"ok": False, "error": "用户名已存在"}

    if email:
        cursor = await db.execute("SELECT id FROM users WHERE email = ? AND email != ''", (email,))
        if await cursor.fetchone():
            return {"ok": False, "error": "该邮箱已被绑定"}

    hashed = get_password_hash(password)
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    cursor = await db.execute(
        "INSERT INTO users (username, hashed_password, email, created_at) VALUES (?, ?, ?, ?)",
        (username, hashed, email, now)
    )
    await db.commit()
    user_id = cursor.lastrowid

    defaults = [
        ("daily_words", "10"),
        ("llm_api_url", "https://api.deepseek.com/v1/chat/completions"),
        ("llm_api_key", ""),
        ("llm_model", "deepseek-chat"),
    ]
    for key, value in defaults:
        await db.execute(
            "INSERT OR IGNORE INTO settings (user_id, key, value) VALUES (?, ?, ?)",
            (user_id, key, value)
        )
    await db.commit()

    return {"ok": True, "user_id": user_id}


async def authenticate(username: str, password: str) -> dict:
    """Authenticate a user. Returns {ok: True, user_id} or {ok: False, error}."""
    db = await get_db()
    cursor = await db.execute(
        "SELECT id, hashed_password FROM users WHERE username = ?", (username,)
    )
    row = await cursor.fetchone()
    if not row:
        return {"ok": False, "error": "用户名或密码错误"}

    if not verify_password(password, row[1]):
        return {"ok": False, "error": "用户名或密码错误"}

    return {"ok": True, "user_id": row[0]}


async def get_user_by_id(user_id: int) -> dict | None:
    """Get user info by ID."""
    db = await get_db()
    cursor = await db.execute("SELECT id, username, email, created_at FROM users WHERE id = ?", (user_id,))
    row = await cursor.fetchone()
    return dict(row) if row else None


async def update_email(user_id: int, email: str) -> dict:
    """Update user email. Returns {ok: True} or {ok: False, error}."""
    db = await get_db()

    if email:
        cursor = await db.execute("SELECT id FROM users WHERE email = ? AND email != '' AND id != ?", (email, user_id))
        if await cursor.fetchone():
            return {"ok": False, "error": "该邮箱已被其他用户绑定"}

    await db.execute("UPDATE users SET email = ? WHERE id = ?", (email, user_id))
    await db.commit()
    return {"ok": True}
