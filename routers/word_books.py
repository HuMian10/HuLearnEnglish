"""Word books API router."""
from fastapi import APIRouter, Depends
from routers.auth import get_current_user_id
from services.word_book_service import (
    get_all_word_books, get_user_active_books,
    activate_book, deactivate_book,
)

router = APIRouter()


@router.get("")
async def list_word_books(user_id: int = Depends(get_current_user_id)):
    all_books = await get_all_word_books()
    active_books = await get_user_active_books(user_id)
    active_ids = {b["id"] for b in active_books}
    for book in all_books:
        book["is_active"] = book["id"] in active_ids
    return {"books": all_books}


@router.get("/my")
async def my_word_books(user_id: int = Depends(get_current_user_id)):
    books = await get_user_active_books(user_id)
    return {"books": books}


@router.post("/{book_id}/activate")
async def activate_word_book(book_id: int, user_id: int = Depends(get_current_user_id)):
    await activate_book(user_id, book_id)
    return {"status": "ok"}


@router.post("/{book_id}/deactivate")
async def deactivate_word_book(book_id: int, user_id: int = Depends(get_current_user_id)):
    ok = await deactivate_book(user_id, book_id)
    if not ok:
        return {"status": "error", "message": "Cannot deactivate the default word book"}
    return {"status": "ok"}
