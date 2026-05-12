"""Words API router."""
from fastapi import APIRouter, Query
from services.word_service import get_words, get_word, get_categories

router = APIRouter()


@router.get("")
async def list_words(
    category: str = Query("", description="Filter by category"),
    search: str = Query("", description="Search word or meaning"),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    word_book_id: int = Query(0, description="Filter by word book id"),
):
    return await get_words(category, search, page, page_size, word_book_id)


@router.get("/categories")
async def list_categories(word_book_id: int = Query(0, description="Filter by word book id")):
    return await get_categories(word_book_id)


@router.get("/{word_id}")
async def word_detail(word_id: int):
    word = await get_word(word_id)
    if not word:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Word not found")
    return word
