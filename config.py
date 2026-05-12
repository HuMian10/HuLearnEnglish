import os

# LLM API 配置
LLM_API_URL = os.getenv("LLM_API_URL", "https://api.deepseek.com/v1/chat/completions")
LLM_API_KEY = os.getenv("LLM_API_KEY", "")
LLM_MODEL = os.getenv("LLM_MODEL", "deepseek-chat")

# 数据库
DB_PATH = os.getenv("DB_PATH", "english_lesson.db")

# 学习设置
DEFAULT_DAILY_WORDS = int(os.getenv("DEFAULT_DAILY_WORDS", "10"))

# JWT 配置
SECRET_KEY = os.getenv("SECRET_KEY", "english-lesson-secret-key-change-in-production")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "1440"))  # 24h

# 服务
HOST = os.getenv("HOST", "0.0.0.0")
PORT = int(os.getenv("PORT", "8000"))
