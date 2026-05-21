"""News API routes."""
import json
import re
from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from routers.auth import get_current_user_id
from services.news_service import get_news_list, get_news_detail, fetch_and_store_news, has_fetched_today
from services.word_service import get_words
from services.llm_service import call_llm_json
from services.learning_service import get_settings
from models.database import get_db

router = APIRouter()


@router.get("/list")
async def news_list(user_id: int = Depends(get_current_user_id)):
    """Get recent news articles."""
    return {"news": await get_news_list(days=3)}


@router.get("/detail")
async def news_detail(id: int = Query(...), user_id: int = Depends(get_current_user_id)):
    """Get a single news article by ID."""
    article = await get_news_detail(id)
    if not article:
        return {"ok": False, "error": "新闻不存在"}
    return {"ok": True, "news": article}


@router.post("/fetch")
async def news_fetch(user_id: int = Depends(get_current_user_id)):
    """Manually trigger news fetching."""
    if await has_fetched_today():
        return {"ok": True, "message": "今天已经抓取过新闻了", "count": 0}
    count = await fetch_and_store_news()
    return {"ok": True, "count": count}


@router.get("/lookup-word")
async def lookup_word(word: str = Query(..., min_length=1), user_id: int = Depends(get_current_user_id)):
    """Look up a single English word in the database."""
    # Normalize: lowercase, strip punctuation
    w = re.sub(r'[^a-zA-Z\'-]', '', word.strip()).lower()
    if not w:
        return {"ok": False, "error": "无效单词"}

    db = await get_db()
    cursor = await db.execute(
        "SELECT id, word, phonetic_uk, phonetic_us, audio_uk, audio_us, meanings, example_en, example_cn FROM words WHERE word = ?",
        (w,)
    )
    row = await cursor.fetchone()
    if not row:
        return {"ok": False, "found": False, "word": w}

    meanings = row[6]
    if isinstance(meanings, str):
        try:
            meanings = json.loads(meanings)
        except (json.JSONDecodeError, TypeError):
            meanings = []

    return {
        "ok": True,
        "found": True,
        "word": {
            "id": row[0],
            "word": row[1],
            "phonetic_uk": row[2],
            "phonetic_us": row[3],
            "audio_uk": row[4],
            "audio_us": row[5],
            "meanings": meanings,
            "example_en": row[7],
            "example_cn": row[8],
        }
    }


class TranslateRequest(BaseModel):
    text: str


@router.post("/translate")
async def translate_text(req: TranslateRequest, user_id: int = Depends(get_current_user_id)):
    """Translate English text to Chinese using LLM."""
    text = req.text.strip()
    if not text:
        return {"ok": False, "error": "空文本"}

    settings = await get_settings(user_id)
    prompt = f"""Translate the following English text to Chinese. The text is from a news article.
Return ONLY valid JSON in this exact format, no other text:
{{
  "translation": "Chinese translation of the text",
  "key_words": [
    {{"word": "English word", "meaning": "Chinese meaning"}},
    {{"word": "another word", "meaning": "another meaning"}}
  ]
}}

English text: {text}"""

    try:
        result = await call_llm_json(prompt, settings)
        return {"ok": True, "data": result}
    except ValueError as e:
        return {"ok": False, "error": str(e)}
    except Exception as e:
        return {"ok": False, "error": f"翻译失败: {str(e)}"}