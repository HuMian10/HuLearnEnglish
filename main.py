from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

from routers import words, learning, llm, auth
from config import DB_PATH
from models.database import init_database

app = FastAPI(title="English Lesson", description="英语日常词汇学习")

app.include_router(auth.router, prefix="/api/auth", tags=["auth"])
app.include_router(words.router, prefix="/api/words", tags=["words"])
app.include_router(learning.router, prefix="/api/learning", tags=["learning"])
app.include_router(learning.plan_router, prefix="/api/plan", tags=["plan"])
app.include_router(llm.router, prefix="/api/llm", tags=["llm"])

app.mount("/static", StaticFiles(directory="static"), name="static")


@app.on_event("startup")
async def startup():
    await init_database(DB_PATH)


@app.get("/")
async def index():
    return FileResponse("static/index.html")


if __name__ == "__main__":
    import uvicorn
    from config import HOST, PORT
    uvicorn.run("main:app", host=HOST, port=PORT, reload=True)
