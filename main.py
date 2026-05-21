import asyncio
from contextlib import asynccontextmanager

from fastapi import FastAPI, Depends
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

from routers import words, learning, llm, auth, word_books
from config import DB_PATH, MORNING_EMAIL_HOUR, EVENING_EMAIL_HOUR, SENDER_PASSWORD
from models.database import init_database
from services.email_service import send_morning_plan_emails, send_evening_summary_emails


async def _email_scheduler():
    """Background task: check every 60s and send scheduled emails."""
    from datetime import datetime

    sent_morning = False
    sent_evening = False

    while True:
        now = datetime.now()
        today = now.strftime("%Y-%m-%d")

        # Reset flags on a new day
        if now.hour == 0 and now.minute < 2:
            sent_morning = False
            sent_evening = False

        # Morning email
        if not sent_morning and now.hour == MORNING_EMAIL_HOUR and now.minute < 2:
            sent_morning = True
            try:
                await send_morning_plan_emails()
            except Exception as e:
                print(f"[email] Morning send error: {e}")

        # Evening email
        if not sent_evening and now.hour == EVENING_EMAIL_HOUR and now.minute < 2:
            sent_evening = True
            try:
                await send_evening_summary_emails()
            except Exception as e:
                print(f"[email] Evening send error: {e}")

        await asyncio.sleep(60)


@asynccontextmanager
async def lifespan(app):
    # Startup
    await init_database(DB_PATH)

    # Start email scheduler only if password is configured
    email_task = None
    if SENDER_PASSWORD:
        email_task = asyncio.create_task(_email_scheduler())
        print(f"[email] Scheduler started (morning={MORNING_EMAIL_HOUR}:00, evening={EVENING_EMAIL_HOUR}:00)")
    else:
        print("[email] SENDER_PASSWORD not set, email scheduler disabled")

    yield

    # Shutdown
    if email_task:
        email_task.cancel()
    from models.database import close_db
    await close_db()


app = FastAPI(title="English Lesson", description="英语日常词汇学习", lifespan=lifespan)

app.include_router(auth.router, prefix="/api/auth", tags=["auth"])
app.include_router(words.router, prefix="/api/words", tags=["words"])
app.include_router(learning.router, prefix="/api/learning", tags=["learning"])
app.include_router(learning.plan_router, prefix="/api/plan", tags=["plan"])
app.include_router(llm.router, prefix="/api/llm", tags=["llm"])
app.include_router(word_books.router, prefix="/api/word-books", tags=["word-books"])

app.mount("/static", StaticFiles(directory="static"), name="static")
app.mount("/audio", StaticFiles(directory="static/audio"), name="audio")


@app.get("/")
async def index():
    return FileResponse("static/index.html")


@app.post("/api/email/test-morning")
async def test_morning_email(user_id: int = Depends(auth.get_current_user_id)):
    """Manually trigger morning plan email for current user."""
    from services.auth_service import get_user_by_id
    from services.email_service import _build_plan_html, _send_email
    user = await get_user_by_id(user_id)
    if not user.get("email"):
        return {"ok": False, "error": "未绑定邮箱"}
    html = await _build_plan_html(user_id, user["username"])
    if not html:
        return {"ok": False, "error": "今日没有学习计划"}
    ok = await _send_email(user["email"], "☀️ 今日学习计划", html)
    return {"ok": ok}


@app.post("/api/email/test-evening")
async def test_evening_email(user_id: int = Depends(auth.get_current_user_id)):
    """Manually trigger evening summary email for current user."""
    from services.auth_service import get_user_by_id
    from services.email_service import _build_summary_html, _send_email
    user = await get_user_by_id(user_id)
    if not user.get("email"):
        return {"ok": False, "error": "未绑定邮箱"}
    html = await _build_summary_html(user_id, user["username"])
    if not html:
        return {"ok": False, "error": "今日没有学习记录"}
    ok = await _send_email(user["email"], "🌙 今日学习总结", html)
    return {"ok": ok}
