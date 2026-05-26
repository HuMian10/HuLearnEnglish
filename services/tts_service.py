"""TTS service using KittenTTS for text-to-speech."""

import os
import hashlib
import asyncio
from pathlib import Path
from config import TTS_MODEL_PATH, TTS_CACHE_DIR, TTS_DEFAULT_VOICE, TTS_SAMPLE_RATE, TTS_MAX_TEXT_LENGTH

_tts_model = None


def _ensure_cache_dir():
    os.makedirs(TTS_CACHE_DIR, exist_ok=True)


def _get_tts_model():
    """Lazy-load the KittenTTS model (only on first request)."""
    global _tts_model
    if _tts_model is None:
        from kittentts import KittenTTS
        model_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), TTS_MODEL_PATH)
        _tts_model = KittenTTS(model_path, cache_dir=model_path)
    return _tts_model


def _cache_key(text: str, voice: str) -> str:
    """Generate a deterministic cache key from text + voice."""
    return hashlib.md5(f"{text}|{voice}".encode()).hexdigest()


def _generate_and_cache(text: str, voice: str = TTS_DEFAULT_VOICE) -> str:
    """Generate TTS audio and save to cache. Returns the file path."""
    _ensure_cache_dir()
    key = _cache_key(text, voice)
    wav_path = os.path.join(TTS_CACHE_DIR, f"{key}.wav")

    # Return cached file if it already exists
    if os.path.exists(wav_path):
        return wav_path

    # Generate audio (CPU-intensive, runs in thread pool)
    import soundfile as sf
    model = _get_tts_model()
    audio = model.generate(text, voice=voice)
    sf.write(wav_path, audio, TTS_SAMPLE_RATE)

    return wav_path


async def generate_tts(text: str, voice: str = TTS_DEFAULT_VOICE) -> str:
    """Async wrapper: generate TTS audio in a thread pool to avoid blocking the event loop."""
    # Truncate very long text to avoid excessive generation time
    text = text.strip()[:TTS_MAX_TEXT_LENGTH]
    if not text:
        raise ValueError("Empty text")

    loop = asyncio.get_event_loop()
    wav_path = await loop.run_in_executor(None, _generate_and_cache, text, voice)
    return wav_path
