"""Enrich words table with detailed info via LLM + Edge TTS audio.

Usage:
    python enrich_details.py                  # fill all missing fields
    python enrich_details.py 50               # process first 50 words
    python enrich_details.py --text           # text info only (LLM)
    python enrich_details.py --audio          # audio only (Edge TTS)
    python enrich_details.py --force          # re-fill even if field not empty
    python enrich_details.py --force --audio  # re-generate all audio
"""
import asyncio
import json
import os
import re
import sqlite3
import subprocess
import sys

import aiohttp

DB_PATH = os.getenv("DB_PATH", "english_lesson.db")
AUDIO_DIR = os.path.join(os.path.dirname(__file__), "static", "audio")

LLM_API_URL = os.getenv("LLM_API_URL", "https://dashscope.aliyuncs.com/compatible-mode/v1/chat/completions")
LLM_API_KEY = os.getenv("LLM_API_KEY", "")
LLM_MODEL = os.getenv("LLM_MODEL", "qwen-plus")

LLM_BATCH_SIZE = 15
AUDIO_CONCURRENCY = 10


def get_llm_config():
    url, key, model = LLM_API_URL, LLM_API_KEY, LLM_MODEL
    try:
        conn = sqlite3.connect(DB_PATH)
        cur = conn.cursor()
        for k, default in [("llm_api_url", url), ("llm_api_key", key), ("llm_model", model)]:
            row = cur.execute("SELECT value FROM settings WHERE key = ?", (k,)).fetchone()
            if row and row[0]:
                if k == "llm_api_url":
                    url = row[0]
                elif k == "llm_api_key":
                    key = row[0]
                elif k == "llm_model":
                    model = row[0]
        conn.close()
    except Exception:
        pass
    return url, key, model


def ensure_audio_dir():
    os.makedirs(os.path.join(AUDIO_DIR, "uk"), exist_ok=True)
    os.makedirs(os.path.join(AUDIO_DIR, "us"), exist_ok=True)


# ── LLM: fill text fields ──────────────────────────────────────────

LLM_PROMPT = """You are a professional English dictionary data generator. For each word below, generate the following information in strict JSON format.

IMPORTANT REQUIREMENTS FOR "meanings":
- Include ALL common meanings and senses of the word.
- Meanings must be as complete and detailed as possible.
- Do NOT merge multiple senses into one short Chinese translation.
- Different meanings under the same part of speech should be listed as separate objects.
- Include both literal and extended/common usages when applicable.
- The output should resemble professional dictionary entries.
- Avoid overly short or generic translations.

For each numbered word, return a JSON object with these fields:
- "phonetic_uk": UK pronunciation in IPA (e.g. /ˈæp.əl/)
- "phonetic_us": US pronunciation in IPA (e.g. /ˈæp.əl/)
- "meanings": array of objects, each with:
    - "pos": part of speech like "noun", "verb", "adj"
    - "meaning_cn": detailed Chinese meaning
  Include ALL common meanings.
- "plural": plural form (only for nouns, empty string if not applicable)
- "past_tense": past tense (only for verbs, empty string if not applicable)
- "past_participle": past participle (only for verbs, empty string if not applicable)
- "present_participle": present participle / gerund (only for verbs, empty string if not applicable)
- "comparative": comparative form (only for adj/adv, empty string if not applicable)
- "superlative": superlative form (only for adj/adv, empty string if not applicable)
- "third_person": third person singular (only for verbs, empty string if not applicable)
- "example_en": ONE natural English example sentence using the word
- "example_cn": Chinese translation of the example sentence

Return ONLY a JSON object mapping the number to the word's data. No explanation.

Words:
{word_list}"""


async def fill_text_info(limit=0, force=False):
    url, key, model = get_llm_config()
    if not key:
        print("Error: No LLM API key. Set LLM_API_KEY env or configure in app Settings.")
        return

    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    if force:
        query = "SELECT id, word, pos, meaning_cn FROM words ORDER BY frequency_rank"
    else:
        query = """SELECT id, word, pos, meaning_cn FROM words
                   WHERE phonetic_uk = '' OR phonetic_us = ''
                   ORDER BY frequency_rank"""
    if limit > 0:
        query += f" LIMIT {limit}"

    rows = cur.execute(query).fetchall()
    if not rows:
        print("All words already have text info!")
        conn.close()
        return

    total = len(rows)
    print(f"Filling text info for {total} words (batch={LLM_BATCH_SIZE})...")

    updated = 0
    failed = 0

    async with aiohttp.ClientSession() as session:
        for offset in range(0, total, LLM_BATCH_SIZE):
            batch = rows[offset:offset + LLM_BATCH_SIZE]
            word_list = "\n".join(
                f'{i}. {row[1]} ({row[2]}): {row[3]}' for i, row in enumerate(batch)
            )
            prompt = LLM_PROMPT.format(word_list=word_list)

            try:
                async with session.post(
                    url,
                    headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
                    json={
                        "model": model,
                        "messages": [{"role": "user", "content": prompt}],
                        "max_tokens": 4096,
                        "temperature": 0.1,
                    },
                    timeout=aiohttp.ClientTimeout(total=120),
                ) as resp:
                    if resp.status != 200:
                        body = await resp.text()
                        print(f"  LLM API error {resp.status}: {body[:200]}")
                        failed += len(batch)
                        continue
                    result = await resp.json()
                    content = result["choices"][0]["message"]["content"]

                content = re.sub(r"```json\s*", "", content)
                content = re.sub(r"```\s*", "", content)
                content = content.strip()
                data = json.loads(content)

                for i, row in enumerate(batch):
                    word_id = row[0]
                    d = data.get(str(i), {})
                    if not d:
                        failed += 1
                        continue

                    meanings = d.get("meanings", [])
                    if not meanings:
                        # fallback: use existing pos/meaning_cn
                        meanings = [{"pos": row[2], "meaning_cn": row[3]}]

                    cur.execute(
                        """UPDATE words SET
                           phonetic_uk=?, phonetic_us=?,
                           meanings=?,
                           plural=?, past_tense=?, past_participle=?,
                           present_participle=?, comparative=?, superlative=?, third_person=?,
                           example_en=?, example_cn=?
                           WHERE id=?""",
                        (
                            d.get("phonetic_uk", ""),
                            d.get("phonetic_us", ""),
                            json.dumps(meanings, ensure_ascii=False),
                            d.get("plural", ""),
                            d.get("past_tense", ""),
                            d.get("past_participle", ""),
                            d.get("present_participle", ""),
                            d.get("comparative", ""),
                            d.get("superlative", ""),
                            d.get("third_person", ""),
                            d.get("example_en", ""),
                            d.get("example_cn", ""),
                            word_id,
                        )
                    )
                    updated += 1

            except (json.JSONDecodeError, KeyError) as e:
                print(f"  Batch parse error: {e}")
                failed += len(batch)
            except Exception as e:
                print(f"  Batch error: {e}")
                failed += len(batch)

            conn.commit()
            done = min(offset + LLM_BATCH_SIZE, total)
            print(f"  Progress: {done}/{total} | updated={updated} failed={failed}")
            await asyncio.sleep(0.5)

    conn.close()
    print(f"Done! Updated {updated}, failed {failed} out of {total}.")


# ── Edge TTS: generate audio ────────────────────────────────────────

EDGE_TTS_UK_VOICE = "en-GB-SoniaNeural"
EDGE_TTS_US_VOICE = "en-US-JennyNeural"


async def generate_audio_for_word(word: str, semaphore: asyncio.Semaphore) -> dict:
    """Generate UK and US audio for a word using edge-tts CLI."""
    async with semaphore:
        safe_word = re.sub(r"[^a-zA-Z0-9_-]", "_", word)
        uk_path = os.path.join(AUDIO_DIR, "uk", f"{safe_word}.mp3")
        us_path = os.path.join(AUDIO_DIR, "us", f"{safe_word}.mp3")
        uk_url = f"/audio/uk/{safe_word}.mp3"
        us_url = f"/audio/us/{safe_word}.mp3"

        results = {"audio_uk": "", "audio_us": ""}

        for voice, path, url_key in [
            (EDGE_TTS_UK_VOICE, uk_path, "audio_uk"),
            (EDGE_TTS_US_VOICE, us_path, "audio_us"),
        ]:
            if os.path.exists(path):
                results[url_key] = f"/audio/{'uk' if 'uk' in url_key else 'us'}/{safe_word}.mp3"
                continue
            try:
                proc = await asyncio.create_subprocess_exec(
                    "edge-tts", "--voice", voice, "--text", word, "--write-media", path,
                    stdout=asyncio.subprocess.DEVNULL,
                    stderr=asyncio.subprocess.DEVNULL,
                )
                await asyncio.wait_for(proc.wait(), timeout=15)
                if proc.returncode == 0 and os.path.exists(path):
                    results[url_key] = f"/audio/{'uk' if 'uk' in url_key else 'us'}/{safe_word}.mp3"
                else:
                    # Clean up partial file
                    if os.path.exists(path):
                        os.remove(path)
            except (asyncio.TimeoutError, FileNotFoundError, Exception):
                if os.path.exists(path):
                    os.remove(path)

        return results


async def fill_audio(limit=0, force=False):
    """Generate UK/US audio for words using Edge TTS."""
    ensure_audio_dir()

    # Check edge-tts is available
    try:
        proc = await asyncio.create_subprocess_exec(
            "edge-tts", "--version",
            stdout=asyncio.subprocess.DEVNULL,
            stderr=asyncio.subprocess.DEVNULL,
        )
        await proc.wait()
    except FileNotFoundError:
        print("Error: edge-tts not found. Install with: pip install edge-tts")
        return

    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    if force:
        query = "SELECT id, word FROM words ORDER BY frequency_rank"
    else:
        query = """SELECT id, word FROM words
                   WHERE audio_uk = '' OR audio_us = ''
                   ORDER BY frequency_rank"""
    if limit > 0:
        query += f" LIMIT {limit}"

    rows = cur.execute(query).fetchall()
    if not rows:
        print("All words already have audio!")
        conn.close()
        return

    total = len(rows)
    print(f"Generating audio for {total} words (concurrency={AUDIO_CONCURRENCY})...")

    semaphore = asyncio.Semaphore(AUDIO_CONCURRENCY)
    updated = 0
    failed = 0

    chunk_size = 50
    for offset in range(0, total, chunk_size):
        chunk = rows[offset:offset + chunk_size]
        tasks = [generate_audio_for_word(word, semaphore) for _, word in chunk]
        results = await asyncio.gather(*tasks)

        for (word_id, word), audio in zip(chunk, results):
            if audio["audio_uk"] or audio["audio_us"]:
                cur.execute(
                    "UPDATE words SET audio_uk=?, audio_us=? WHERE id=?",
                    (audio["audio_uk"], audio["audio_us"], word_id)
                )
                updated += 1
            else:
                failed += 1

        conn.commit()
        done = min(offset + chunk_size, total)
        print(f"  Progress: {done}/{total} | updated={updated} failed={failed}")

    conn.close()
    print(f"Done! Audio generated for {updated}, failed {failed} out of {total}.")


# ── Main ────────────────────────────────────────────────────────────

def print_usage():
    print("Usage: python enrich_details.py [options] [limit]")
    print()
    print("Options:")
    print("  --text     Fill text info only (phonetics, meanings, forms, examples)")
    print("  --audio    Generate audio only (UK + US via Edge TTS)")
    print("  --force    Re-fill even if fields are not empty")
    print("  --help     Show this help")
    print()
    print("Default: fill both text and audio for words with missing fields")
    print()
    print("Examples:")
    print("  python enrich_details.py              # fill all missing")
    print("  python enrich_details.py 50           # first 50 words")
    print("  python enrich_details.py --text       # text info only")
    print("  python enrich_details.py --audio      # audio only")
    print("  python enrich_details.py --force      # re-fill everything")


def main():
    args = sys.argv[1:]
    if "--help" in args or "-h" in args:
        print_usage()
        return

    do_text = True
    do_audio = True
    force = False
    limit = 0

    for arg in args:
        if arg == "--text":
            do_audio = False
        elif arg == "--audio":
            do_text = False
        elif arg == "--force":
            force = True
        elif arg.isdigit():
            limit = int(arg)

    if do_text:
        asyncio.run(fill_text_info(limit, force))
    if do_audio:
        asyncio.run(fill_audio(limit, force))


if __name__ == "__main__":
    main()
