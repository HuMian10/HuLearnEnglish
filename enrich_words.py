"""Enrich words with phonetics and examples from Free Dictionary API (async + concurrent).

Also translates example sentences to Chinese via LLM API.

Usage:
    python enrich_words.py              # enrich all words missing phonetics
    python enrich_words.py 50           # enrich first 50 words only
    python enrich_words.py --translate   # translate existing example sentences
    python enrich_words.py --all        # force re-fetch all words
"""
import asyncio
import json
import os
import re
import sqlite3
import sys

import aiohttp

DB_PATH = os.getenv("DB_PATH", "english_lesson.db")
DICT_API = "https://api.dictionaryapi.dev/api/v2/entries/en/"

# Concurrency settings
MAX_CONCURRENT = 20          # parallel dictionary API requests
BATCH_COMMIT = 50            # commit to DB every N updates
LLM_BATCH_SIZE = 30          # translate N sentences per LLM call

# LLM config (reads from DB settings or env vars)
LLM_API_URL = os.getenv("LLM_API_URL", "https://api.deepseek.com/v1/chat/completions")
LLM_API_KEY = os.getenv("LLM_API_KEY", "")
LLM_MODEL = os.getenv("LLM_MODEL", "deepseek-chat")


def get_llm_config():
    """Try to read LLM config from DB settings, fallback to env."""
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


async def fetch_word(session: aiohttp.ClientSession, word: str, semaphore: asyncio.Semaphore):
    """Fetch phonetic + example from Free Dictionary API."""
    async with semaphore:
        try:
            url = DICT_API + word
            async with session.get(url, timeout=aiohttp.ClientTimeout(total=10)) as resp:
                if resp.status != 200:
                    return None
                data = await resp.json()

            if not data or not isinstance(data, list):
                return None

            entry = data[0]

            # Extract phonetic
            phonetic = entry.get("phonetic", "")
            if not phonetic:
                for p in entry.get("phonetics", []):
                    if p.get("text"):
                        phonetic = p["text"]
                        break

            # Extract first example sentence
            example_en = ""
            for meaning in entry.get("meanings", []):
                for defn in meaning.get("definitions", []):
                    if defn.get("example"):
                        example_en = defn["example"]
                        break
                if example_en:
                    break

            return {"phonetic": phonetic, "example_en": example_en}
        except Exception:
            return None


async def enrich_phonetics(limit=0, force=False):
    """Fetch phonetics and examples concurrently from dictionary API."""
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    if force:
        query = "SELECT id, word FROM words ORDER BY frequency_rank"
        if limit > 0:
            query += f" LIMIT {limit}"
    else:
        query = "SELECT id, word FROM words WHERE phonetic = '' OR phonetic IS NULL ORDER BY frequency_rank"
        if limit > 0:
            query += f" LIMIT {limit}"

    rows = cur.execute(query).fetchall()
    total = len(rows)
    if total == 0:
        print("All words already have phonetics!")
        conn.close()
        return

    print(f"Enriching {total} words (concurrency={MAX_CONCURRENT})...")

    semaphore = asyncio.Semaphore(MAX_CONCURRENT)
    enriched = 0
    failed = 0

    async with aiohttp.ClientSession() as session:
        # Process in chunks to show progress
        chunk_size = 100
        for offset in range(0, total, chunk_size):
            chunk = rows[offset:offset + chunk_size]
            tasks = [fetch_word(session, word, semaphore) for _, word in chunk]
            results = await asyncio.gather(*tasks)

            for (word_id, word), data in zip(chunk, results):
                if data and (data["phonetic"] or data["example_en"]):
                    cur.execute(
                        "UPDATE words SET phonetic=?, example_en=? WHERE id=?",
                        (data["phonetic"], data["example_en"], word_id)
                    )
                    enriched += 1
                else:
                    failed += 1

            conn.commit()
            done = min(offset + chunk_size, total)
            print(f"  Progress: {done}/{total} | enriched={enriched} failed={failed}")

    conn.commit()
    conn.close()
    print(f"Done! Enriched {enriched}, failed {failed} out of {total}.")


async def translate_examples(limit=0):
    """Translate existing English example sentences to Chinese using LLM.

    Sends sentences in batches to minimize API calls.
    """
    url, key, model = get_llm_config()
    if not key:
        print("Error: No LLM API key configured.")
        print("Set LLM_API_KEY env var or configure in the app's Settings page.")
        return

    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    query = """SELECT id, word, example_en FROM words
               WHERE example_en != '' AND example_en IS NOT NULL
               AND (example_cn = '' OR example_cn IS NULL)
               ORDER BY frequency_rank"""
    if limit > 0:
        query += f" LIMIT {limit}"

    rows = cur.execute(query).fetchall()
    if not rows:
        print("No sentences to translate!")
        conn.close()
        return

    total = len(rows)
    print(f"Translating {total} example sentences (batch_size={LLM_BATCH_SIZE})...")

    translated = 0
    failed = 0

    async with aiohttp.ClientSession() as session:
        for offset in range(0, total, LLM_BATCH_SIZE):
            batch = rows[offset:offset + LLM_BATCH_SIZE]

            # Build the prompt with numbered sentences
            sentences = {i: row[2] for i, row in enumerate(batch)}
            numbered = "\n".join(f"{i}. {s}" for i, s in sentences.items())

            prompt = (
                "Translate the following English sentences to Chinese. "
                "Return ONLY a JSON object mapping the number to the Chinese translation. "
                "Do not add any explanation.\n\n" + numbered
            )

            try:
                async with session.post(
                    url,
                    headers={
                        "Authorization": f"Bearer {key}",
                        "Content-Type": "application/json",
                    },
                    json={
                        "model": model,
                        "messages": [{"role": "user", "content": prompt}],
                        "max_tokens": 2048,
                        "temperature": 0.1,
                    },
                    timeout=aiohttp.ClientTimeout(total=60),
                ) as resp:
                    if resp.status != 200:
                        body = await resp.text()
                        print(f"  LLM API error {resp.status}: {body[:200]}")
                        failed += len(batch)
                        continue

                    result = await resp.json()
                    content = result["choices"][0]["message"]["content"]

                # Parse the JSON response
                # LLM might return ```json ... ``` or raw JSON
                content = re.sub(r"```json\s*", "", content)
                content = re.sub(r"```\s*", "", content)
                content = content.strip()

                translations = json.loads(content)

                for i, row in enumerate(batch):
                    word_id = row[0]
                    cn = translations.get(str(i), "")
                    if cn:
                        cur.execute(
                            "UPDATE words SET example_cn=? WHERE id=?",
                            (cn, word_id)
                        )
                        translated += 1
                    else:
                        failed += 1

            except (json.JSONDecodeError, KeyError, Exception) as e:
                print(f"  Batch translation error: {e}")
                failed += len(batch)

            conn.commit()
            done = min(offset + LLM_BATCH_SIZE, total)
            print(f"  Progress: {done}/{total} | translated={translated} failed={failed}")

            # Small delay to avoid rate limiting
            await asyncio.sleep(0.5)

    conn.commit()
    conn.close()
    print(f"Done! Translated {translated}, failed {failed} out of {total}.")


async def generate_examples(limit=0):
    """Use LLM to generate example sentences + Chinese translations for words that lack them.

    This is a fallback for words where the dictionary API had no example.
    """
    url, key, model = get_llm_config()
    if not key:
        print("Error: No LLM API key configured.")
        print("Set LLM_API_KEY env var or configure in the app's Settings page.")
        return

    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    query = """SELECT id, word, pos, meaning_cn FROM words
               WHERE (example_en = '' OR example_en IS NULL)
               ORDER BY frequency_rank"""
    if limit > 0:
        query += f" LIMIT {limit}"

    rows = cur.execute(query).fetchall()
    if not rows:
        print("All words already have example sentences!")
        conn.close()
        return

    total = len(rows)
    batch_size = 20
    print(f"Generating examples for {total} words (batch_size={batch_size})...")

    generated = 0

    async with aiohttp.ClientSession() as session:
        for offset in range(0, total, batch_size):
            batch = rows[offset:offset + batch_size]

            # Build prompt
            word_list = "\n".join(
                f'{i}. {row[1]} ({row[2]}): {row[3]}' for i, row in enumerate(batch)
            )
            prompt = (
                "For each word below, write ONE natural English example sentence and its Chinese translation. "
                "Return ONLY a JSON object mapping the number to {\"en\": \"English sentence\", \"cn\": \"Chinese translation\"}. "
                "Do not add any explanation.\n\n" + word_list
            )

            try:
                async with session.post(
                    url,
                    headers={
                        "Authorization": f"Bearer {key}",
                        "Content-Type": "application/json",
                    },
                    json={
                        "model": model,
                        "messages": [{"role": "user", "content": prompt}],
                        "max_tokens": 2048,
                        "temperature": 0.3,
                    },
                    timeout=aiohttp.ClientTimeout(total=60),
                ) as resp:
                    if resp.status != 200:
                        body = await resp.text()
                        print(f"  LLM API error {resp.status}: {body[:200]}")
                        continue

                    result = await resp.json()
                    content = result["choices"][0]["message"]["content"]

                content = re.sub(r"```json\s*", "", content)
                content = re.sub(r"```\s*", "", content)
                content = content.strip()
                examples = json.loads(content)

                for i, row in enumerate(batch):
                    word_id = row[0]
                    ex = examples.get(str(i), {})
                    en = ex.get("en", "")
                    cn = ex.get("cn", "")
                    if en:
                        cur.execute(
                            "UPDATE words SET example_en=?, example_cn=? WHERE id=?",
                            (en, cn, word_id)
                        )
                        generated += 1

            except (json.JSONDecodeError, KeyError, Exception) as e:
                print(f"  Batch generation error: {e}")

            conn.commit()
            done = min(offset + batch_size, total)
            print(f"  Progress: {done}/{total} | generated={generated}")

            await asyncio.sleep(0.5)

    conn.commit()
    conn.close()
    print(f"Done! Generated examples for {generated} out of {total}.")


def print_usage():
    print("Usage: python enrich_words.py [command] [limit]")
    print()
    print("Commands:")
    print("  (default)     Enrich phonetics from dictionary API")
    print("  --translate   Translate existing example sentences to Chinese via LLM")
    print("  --generate    Generate example sentences for words missing them via LLM")
    print("  --all         Force re-fetch all words (not just missing)")
    print()
    print("Options:")
    print("  limit         Number of words to process (0 = all)")
    print()
    print("Examples:")
    print("  python enrich_words.py              # fetch phonetics for all missing")
    print("  python enrich_words.py 50           # fetch first 50")
    print("  python enrich_words.py --translate  # translate all example sentences")
    print("  python enrich_words.py --translate 100  # translate first 100")
    print("  python enrich_words.py --generate   # generate examples for words missing them")


def main():
    args = sys.argv[1:]
    if "--help" in args or "-h" in args:
        print_usage()
        return

    command = "phonetics"
    limit = 0

    for arg in args:
        if arg == "--translate":
            command = "translate"
        elif arg == "--generate":
            command = "generate"
        elif arg == "--all":
            command = "all"
        elif arg.isdigit():
            limit = int(arg)

    if command == "phonetics":
        asyncio.run(enrich_phonetics(limit, force=False))
    elif command == "all":
        asyncio.run(enrich_phonetics(limit, force=True))
    elif command == "translate":
        asyncio.run(translate_examples(limit))
    elif command == "generate":
        asyncio.run(generate_examples(limit))


if __name__ == "__main__":
    main()
