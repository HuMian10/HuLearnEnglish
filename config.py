"""
Configuration loader: reads config.yaml, with environment variable overrides.

Priority: Environment variable > config.yaml > default
Environment variables use UPPER_SNAKE_CASE with section prefix, e.g.:
  LLM_API_KEY  -> llm.api_key
  DB_PATH      -> database.path
  SECRET_KEY   -> jwt.secret_key
"""

import os
from pathlib import Path

# Resolve project root (where config.yaml lives)
_PROJECT_ROOT = Path(__file__).parent.resolve()
_YAML_PATH = _PROJECT_ROOT / "config.yaml"


def _load_yaml() -> dict:
    """Load and parse config.yaml."""
    if not _YAML_PATH.exists():
        print(f"[config] WARNING: {_YAML_PATH} not found, using defaults")
        return {}
    try:
        import yaml
        with open(_YAML_PATH, "r", encoding="utf-8") as f:
            return yaml.safe_load(f) or {}
    except ImportError:
        print("[config] WARNING: PyYAML not installed, using defaults")
        return {}


def _get(cfg: dict, section: str, key: str, default=None):
    """Get a value from cfg[section][key], fallback to default."""
    return cfg.get(section, {}).get(key, default)


def _env(name: str, default=None):
    """Read environment variable."""
    val = os.getenv(name)
    if val is None:
        return default
    return val


def _env_int(name: str, default: int) -> int:
    """Read environment variable as int."""
    val = os.getenv(name)
    if val is None:
        return default
    try:
        return int(val)
    except (ValueError, TypeError):
        return default


# ─── Load once at import time ───
_cfg = _load_yaml()

# ─── Server ───
HOST = _env("HOST", _get(_cfg, "server", "host", "0.0.0.0"))
PORT = _env_int("PORT", _get(_cfg, "server", "port", 8000))

# ─── Database ───
DB_PATH = _env("DB_PATH", _get(_cfg, "database", "path", "english_lesson.db"))

# ─── JWT ───
SECRET_KEY = _env("SECRET_KEY", _get(_cfg, "jwt", "secret_key", "english-lesson-secret-key-change-in-production"))
ALGORITHM = _get(_cfg, "jwt", "algorithm", "HS256")
ACCESS_TOKEN_EXPIRE_MINUTES = _env_int("ACCESS_TOKEN_EXPIRE_MINUTES", _get(_cfg, "jwt", "access_token_expire_minutes", 1440))

# ─── Learning ───
DEFAULT_DAILY_WORDS = _env_int("DEFAULT_DAILY_WORDS", _get(_cfg, "learning", "default_daily_words", 10))

# ─── LLM ───
LLM_API_URL = _env("LLM_API_URL", _get(_cfg, "llm", "api_url", "https://api.deepseek.com/v1/chat/completions"))
LLM_API_KEY = _env("LLM_API_KEY", _get(_cfg, "llm", "api_key", ""))
LLM_MODEL = _env("LLM_MODEL", _get(_cfg, "llm", "model", "deepseek-chat"))

# ─── Email ───
SMTP_SERVER = _env("SMTP_SERVER", _get(_cfg, "email", "smtp_server", "smtp.163.com"))
SMTP_PORT = _env_int("SMTP_PORT", _get(_cfg, "email", "smtp_port", 465))
SENDER_EMAIL = _env("SENDER_EMAIL", _get(_cfg, "email", "sender_email", ""))
SENDER_PASSWORD = _env("SENDER_PASSWORD", _get(_cfg, "email", "sender_password", ""))
MORNING_EMAIL_HOUR = _env_int("MORNING_EMAIL_HOUR", _get(_cfg, "email", "morning_hour", 8))
EVENING_EMAIL_HOUR = _env_int("EVENING_EMAIL_HOUR", _get(_cfg, "email", "evening_hour", 21))

# ─── News ───
NEWS_FETCH_HOUR = _env_int("NEWS_FETCH_HOUR", _get(_cfg, "news", "fetch_hour", 9))
NEWS_FETCH_COUNT = _env_int("NEWS_FETCH_COUNT", _get(_cfg, "news", "fetch_count", 20))
NEWS_RETENTION_DAYS = _env_int("NEWS_RETENTION_DAYS", _get(_cfg, "news", "retention_days", 7))
NEWS_LIST_DAYS = _env_int("NEWS_LIST_DAYS", _get(_cfg, "news", "list_days", 7))
NEWS_LIST_LIMIT = _env_int("NEWS_LIST_LIMIT", _get(_cfg, "news", "list_limit", 60))
NEWS_SOURCE_URL = _env("NEWS_SOURCE_URL", _get(_cfg, "news", "source_url", "https://www.aibase.com/zh/news/"))
NEWS_API_URL = _env("NEWS_API_URL", _get(_cfg, "news", "api_url", "https://mcpapi.aibase.cn/api/aiInfo/detail"))

# ─── TTS ───
TTS_MODEL_PATH = _env("TTS_MODEL_PATH", _get(_cfg, "tts", "model_path", "checkpoints/kittentts_int8"))
TTS_CACHE_DIR = _env("TTS_CACHE_DIR", _get(_cfg, "tts", "cache_dir", "static/tts_cache"))
TTS_DEFAULT_VOICE = _env("TTS_DEFAULT_VOICE", _get(_cfg, "tts", "default_voice", "Jasper"))
TTS_SAMPLE_RATE = _env_int("TTS_SAMPLE_RATE", _get(_cfg, "tts", "sample_rate", 24000))
TTS_MAX_TEXT_LENGTH = _env_int("TTS_MAX_TEXT_LENGTH", _get(_cfg, "tts", "max_text_length", 500))
