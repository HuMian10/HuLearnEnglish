"""LLM chat API router."""
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from routers.auth import get_current_user_id
from services.llm_service import stream_chat, call_llm_json, build_action_prompt
from services.learning_service import get_settings
from services.word_service import get_word

router = APIRouter()


class ChatRequest(BaseModel):
    word: str
    message: str


@router.post("/chat")
async def chat(req: ChatRequest, user_id: int = Depends(get_current_user_id)):
    """Free-form chat with LLM (streaming SSE)."""
    settings = await get_settings(user_id)
    return StreamingResponse(
        stream_chat(req.word, req.message, settings),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        }
    )


@router.post("/quick-actions/{word_id}")
async def quick_action(word_id: int, action: str = "examples", user_id: int = Depends(get_current_user_id)):
    """Quick LLM actions returning structured JSON.

    Actions: examples, explain, quiz
    Returns parsed JSON data from LLM for frontend rendering.
    """
    if action not in ("examples", "explain", "quiz"):
        raise HTTPException(status_code=400, detail="Invalid action. Use: examples, explain, quiz")

    word_data = await get_word(word_id)
    if not word_data:
        raise HTTPException(status_code=404, detail="Word not found")

    settings = await get_settings(user_id)
    prompt = build_action_prompt(action, word_data)

    try:
        result = await call_llm_json(prompt, settings)
    except ValueError as e:
        return {"ok": False, "error": str(e)}
    except Exception as e:
        # If JSON parse fails, return raw text as fallback
        return {"ok": False, "error": f"Failed to parse LLM response: {str(e)}"}

    return {"ok": True, "action": action, "data": result}
