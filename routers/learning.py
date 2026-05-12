"""Learning and plan API routers."""
from fastapi import APIRouter, Depends
from pydantic import BaseModel
from routers.auth import get_current_user_id
from services.learning_service import (
    generate_daily_plan, get_today_plan, submit_review,
    get_learning_stats, get_plan_words, get_settings, update_setting,
    get_calendar_month, get_day_detail, clear_day_progress, clear_all_plans,
    get_due_review_words, continue_plan,
)

plan_router = APIRouter()
router = APIRouter()


class ReviewRequest(BaseModel):
    word_id: int
    correct: bool


class SettingRequest(BaseModel):
    key: str
    value: str


# --- Plan routes ---

@plan_router.get("/today")
async def today_plan(user_id: int = Depends(get_current_user_id)):
    plan = await get_today_plan(user_id)
    if not plan:
        return {"plan": None, "words": [], "remaining": []}
    words, remaining = await get_plan_words(user_id)
    return {
        "plan": plan,
        "words": words,
        "remaining": remaining,
    }


@plan_router.post("/generate")
async def generate_plan(user_id: int = Depends(get_current_user_id)):
    plan = await generate_daily_plan(user_id)
    if not plan:
        return {"message": "No new words to learn and no reviews due!"}
    words, remaining = await get_plan_words(user_id)
    return {"plan": plan, "words": words, "remaining": remaining}


@plan_router.post("/continue")
async def continue_learning(user_id: int = Depends(get_current_user_id)):
    plan = await continue_plan(user_id)
    if not plan:
        return {"message": "No more new words available!"}
    words, remaining = await get_plan_words(user_id)
    return {"plan": plan, "words": words, "remaining": remaining}


# --- Learning routes ---

@router.post("/review")
async def review_word(req: ReviewRequest, user_id: int = Depends(get_current_user_id)):
    await submit_review(user_id, req.word_id, req.correct)
    stats = await get_learning_stats(user_id)
    return {"status": "ok", "stats": stats}


@router.get("/stats")
async def learning_stats(user_id: int = Depends(get_current_user_id)):
    return await get_learning_stats(user_id)


@router.get("/plan-words")
async def plan_words_list(user_id: int = Depends(get_current_user_id)):
    words, remaining = await get_plan_words(user_id)
    return {"words": words, "remaining": remaining}


@router.get("/due-review")
async def due_review_words(user_id: int = Depends(get_current_user_id)):
    words = await get_due_review_words(user_id)
    return {"words": words}


# --- Settings routes ---

@router.get("/settings")
async def get_all_settings(user_id: int = Depends(get_current_user_id)):
    return await get_settings(user_id)


@router.post("/settings")
async def set_setting(req: SettingRequest, user_id: int = Depends(get_current_user_id)):
    await update_setting(user_id, req.key, req.value)
    return {"status": "ok"}


# --- Calendar routes ---

@router.get("/calendar")
async def calendar_month(year: int, month: int, user_id: int = Depends(get_current_user_id)):
    return await get_calendar_month(user_id, year, month)


@router.get("/day-detail")
async def day_detail(date: str, user_id: int = Depends(get_current_user_id)):
    return await get_day_detail(user_id, date)


@router.delete("/day-progress")
async def delete_day_progress(date: str, user_id: int = Depends(get_current_user_id)):
    await clear_day_progress(user_id, date)
    return {"status": "ok"}


@router.delete("/all-plans")
async def delete_all_plans(user_id: int = Depends(get_current_user_id)):
    await clear_all_plans(user_id)
    return {"status": "ok"}
