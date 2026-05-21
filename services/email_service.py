"""Email service - scheduled daily learning plan and summary emails."""
import asyncio
import smtplib
import json
from email.mime.text import MIMEText
from email.header import Header
from datetime import datetime

from models.database import get_db
from config import SMTP_SERVER, SMTP_PORT, SENDER_EMAIL, SENDER_PASSWORD


def _send_email_sync(to: str, subject: str, body: str):
    """Send an HTML email to a single recipient (synchronous)."""
    msg = MIMEText(body, "html", "utf-8")
    msg["From"] = Header(f"Hu Learn English <{SENDER_EMAIL}>")
    msg["To"] = Header(to)
    msg["Subject"] = Header(subject, "utf-8")

    try:
        server = smtplib.SMTP_SSL(SMTP_SERVER, SMTP_PORT)
        server.login(SENDER_EMAIL, SENDER_PASSWORD)
        server.sendmail(SENDER_EMAIL, [to], msg.as_string())
        server.quit()
        return True
    except Exception as e:
        print(f"[email] Failed to send to {to}: {e}")
        return False


async def _send_email(to: str, subject: str, body: str):
    """Send an HTML email asynchronously (non-blocking)."""
    return await asyncio.to_thread(_send_email_sync, to, subject, body)


async def _get_users_with_email():
    """Get all users who have bound an email address."""
    db = await get_db()
    cursor = await db.execute("SELECT id, username, email FROM users WHERE email IS NOT NULL AND email != ''")
    rows = await cursor.fetchall()
    return [{"id": r[0], "username": r[1], "email": r[2]} for r in rows]


async def _build_plan_html(user_id: int, username: str) -> str | None:
    """Build morning email HTML with today's learning plan."""
    db = await get_db()
    today = datetime.now().strftime("%Y-%m-%d")

    # Ensure plan is generated
    from services.learning_service import generate_daily_plan, get_plan_words
    plan = await generate_daily_plan(user_id)
    if not plan:
        return None

    words, remaining = await get_plan_words(user_id)
    if not words:
        return None

    review_count = len(json.loads(plan.get("review_ids", "[]")))
    new_count = len(words) - review_count

    word_rows = ""
    for w in words:
        status = "✅" if w.get("completed") else "⬜"
        # Parse meanings, fallback to legacy pos/meaning_cn
        meanings = []
        raw_meanings = w.get("meanings", "[]")
        if isinstance(raw_meanings, str):
            try:
                meanings = json.loads(raw_meanings)
            except (json.JSONDecodeError, TypeError):
                pass
        elif isinstance(raw_meanings, list):
            meanings = raw_meanings
        if not meanings and w.get("pos") and w.get("meaning_cn"):
            meanings = [{"pos": w["pos"], "meaning_cn": w["meaning_cn"]}]
        # Use first meaning for table
        primary = meanings[0] if meanings else {}
        pos_text = primary.get("pos", w.get("pos", ""))
        meaning_text = primary.get("meaning_cn", w.get("meaning_cn", ""))
        word_rows += f"""
        <tr>
          <td style="padding:8px 12px;border-bottom:1px solid #e2e8f0">{status}</td>
          <td style="padding:8px 12px;border-bottom:1px solid #e2e8f0;font-weight:600">{w['word']}</td>
          <td style="padding:8px 12px;border-bottom:1px solid #e2e8f0;color:#64748b">{pos_text}</td>
          <td style="padding:8px 12px;border-bottom:1px solid #e2e8f0">{meaning_text}</td>
        </tr>"""

    return f"""
    <div style="max-width:600px;margin:0 auto;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,sans-serif;color:#1e293b">
      <div style="background:linear-gradient(135deg,#4f46e5,#818cf8);padding:24px;border-radius:12px 12px 0 0;text-align:center">
        <h1 style="color:white;margin:0;font-size:22px">☀️ 早上好，{username}！</h1>
        <p style="color:rgba(255,255,255,0.85);margin:8px 0 0;font-size:14px">{today} 学习计划</p>
      </div>
      <div style="background:#fff;padding:20px;border:1px solid #e2e8f0;border-top:none">
        <p style="margin:0 0 16px;font-size:15px">
          今日共 <strong>{len(words)}</strong> 个单词
          （新学 {new_count} 个，复习 {review_count} 个）
        </p>
        <table style="width:100%;border-collapse:collapse;font-size:14px">
          <thead>
            <tr style="background:#f8fafc">
              <th style="padding:8px 12px;text-align:left;border-bottom:2px solid #e2e8f0">状态</th>
              <th style="padding:8px 12px;text-align:left;border-bottom:2px solid #e2e8f0">单词</th>
              <th style="padding:8px 12px;text-align:left;border-bottom:2px solid #e2e8f0">词性</th>
              <th style="padding:8px 12px;text-align:left;border-bottom:2px solid #e2e8f0">释义</th>
            </tr>
          </thead>
          <tbody>{word_rows}</tbody>
        </table>
      </div>
      <div style="background:#f8fafc;padding:16px 20px;border:1px solid #e2e8f0;border-top:none;border-radius:0 0 12px 12px;text-align:center">
        <a href="https://hu-learn-english.example.com/learn"
           style="display:inline-block;background:#4f46e5;color:white;padding:12px 32px;border-radius:8px;text-decoration:none;font-weight:600">
          开始学习
        </a>
      </div>
    </div>"""


async def _build_summary_html(user_id: int, username: str) -> str | None:
    """Build evening email HTML with today's learning summary."""
    db = await get_db()
    today = datetime.now().strftime("%Y-%m-%d")

    from services.learning_service import get_learning_stats, get_plan_words
    stats = await get_learning_stats(user_id)
    words, remaining = await get_plan_words(user_id)

    completed = stats.get("today_completed", 0)
    total = stats.get("today_total", 0)
    pct = round(completed / total * 100) if total > 0 else 0

    # Build progress bar
    bar_color = "#10b981" if pct >= 80 else "#f59e0b" if pct >= 50 else "#ef4444"
    progress_bar = f"""
    <div style="background:#e2e8f0;border-radius:8px;height:12px;overflow:hidden;margin:12px 0">
      <div style="background:{bar_color};height:100%;width:{pct}%;border-radius:8px;transition:width 0.5s"></div>
    </div>"""

    # Remaining words
    remain_text = ""
    if remaining:
        words_str = "、".join([f"<strong>{w['word']}</strong>" for w in remaining[:10]])
        if len(remaining) > 10:
            words_str += f" 等 {len(remaining)} 个"
        remain_text = f"""<p style="margin:16px 0 0;font-size:14px;color:#64748b">
          还未完成：{words_str}</p>"""

    return f"""
    <div style="max-width:600px;margin:0 auto;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,sans-serif;color:#1e293b">
      <div style="background:linear-gradient(135deg,#4f46e5,#818cf8);padding:24px;border-radius:12px 12px 0 0;text-align:center">
        <h1 style="color:white;margin:0;font-size:22px">🌙 晚上好，{username}！</h1>
        <p style="color:rgba(255,255,255,0.85);margin:8px 0 0;font-size:14px">{today} 学习总结</p>
      </div>
      <div style="background:#fff;padding:20px;border:1px solid #e2e8f0;border-top:none">
        <div style="text-align:center;margin-bottom:16px">
          <span style="font-size:48px;font-weight:700;color:{bar_color}">{pct}%</span>
          <p style="margin:4px 0 0;font-size:15px">今日完成 {completed}/{total} 个单词</p>
        </div>
        {progress_bar}
        <div style="display:flex;gap:12px;margin-top:16px">
          <div style="flex:1;text-align:center;padding:12px;background:#f0fdf4;border-radius:8px">
            <div style="font-size:24px;font-weight:700;color:#10b981">{stats.get('mastered_count', 0)}</div>
            <div style="font-size:12px;color:#64748b;margin-top:2px">已掌握</div>
          </div>
          <div style="flex:1;text-align:center;padding:12px;background:#fef3c7;border-radius:8px">
            <div style="font-size:24px;font-weight:700;color:#f59e0b">{stats.get('learning_count', 0)}</div>
            <div style="font-size:12px;color:#64748b;margin-top:2px">学习中</div>
          </div>
          <div style="flex:1;text-align:center;padding:12px;background:#eef2ff;border-radius:8px">
            <div style="font-size:24px;font-weight:700;color:#4f46e5">{stats.get('new_count', 0)}</div>
            <div style="font-size:12px;color:#64748b;margin-top:2px">未开始</div>
          </div>
        </div>
        {remain_text}
      </div>
      <div style="background:#f8fafc;padding:16px 20px;border:1px solid #e2e8f0;border-top:none;border-radius:0 0 12px 12px;text-align:center">
        <p style="margin:0;font-size:13px;color:#94a3b8">继续加油，明天见！ 💪</p>
      </div>
    </div>"""


async def send_morning_plan_emails():
    """Send morning learning plan emails to all users with bound email."""
    users = await _get_users_with_email()
    print(f"[email] Morning plan: sending to {len(users)} users")

    for user in users:
        html = await _build_plan_html(user["id"], user["username"])
        if html:
            _send_email(user["email"], "☀️ 今日学习计划", html)

    print(f"[email] Morning plan: done")


async def send_evening_summary_emails():
    """Send evening learning summary emails to all users with bound email."""
    users = await _get_users_with_email()
    print(f"[email] Evening summary: sending to {len(users)} users")

    for user in users:
        html = await _build_summary_html(user["id"], user["username"])
        if html:
            _send_email(user["email"], "🌙 今日学习总结", html)

    print(f"[email] Evening summary: done")
