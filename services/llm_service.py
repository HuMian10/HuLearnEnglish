"""LLM service - handles communication with OpenAI-compatible APIs."""
import json
import re
import httpx

SYSTEM_PROMPT = """You are an English learning assistant for Chinese students.
Help the user learn English words. Always be encouraging and use simple, clear language."""

# Prompt templates that enforce JSON output
ACTION_PROMPTS = {
    "examples": """For the word "{word}", generate 3 natural example sentences.
Return ONLY valid JSON in this exact format, no other text:
{{
  "examples": [
    {{"en": "English sentence using {word}.", "cn": "Chinese translation."}},
    {{"en": "Another English sentence using {word}.", "cn": "Chinese translation."}},
    {{"en": "Third English sentence using {word}.", "cn": "Chinese translation."}}
  ]
}}""",

    "explain": """Explain the word "{word}" (part of speech: {pos}, Chinese meaning: {meaning_cn}) in detail for a Chinese learner.
Return ONLY valid JSON in this exact format, no other text:
{{
  "meaning": "Detailed Chinese explanation of the word's core meaning",
  "nuances": "Explain subtle differences, extended meanings, or cultural context in Chinese",
  "collocations": ["common collocation 1", "common collocation 2", "common collocation 3"],
  "common_mistakes": "Common mistakes Chinese learners make with this word, in Chinese"
}}""",

    "quiz": """Create a short quiz for the word "{word}" (meaning: {meaning_cn}).
Return ONLY valid JSON in this exact format, no other text:
{{
  "quizzes": [
    {{
      "type": "fill_blank",
      "question": "A sentence with ___ where the word should be",
      "answer": "{word}",
      "hint": "A brief hint in Chinese"
    }},
    {{
      "type": "choice",
      "question": "A question about the word's meaning or usage",
      "options": ["A. option", "B. option", "C. option", "D. option"],
      "answer": "A",
      "explanation": "Explanation in Chinese for why this answer is correct"
    }}
  ]
}}""",
}


async def stream_chat(word: str, message: str, settings: dict):
    """Stream chat with LLM about a word. Yields SSE-formatted chunks."""
    api_key = settings.get("llm_api_key", "")
    api_url = settings.get("llm_api_url", "https://api.deepseek.com/v1/chat/completions")
    model = settings.get("llm_model", "deepseek-chat")

    if not api_key:
        yield 'data: {"error": "LLM API key not configured. Please set it in Settings."}\n\n'
        return

    messages = [
        {"role": "system", "content": SYSTEM_PROMPT + f"\n\nThe user is currently learning the word: {word}"},
        {"role": "user", "content": message}
    ]

    try:
        async with httpx.AsyncClient(timeout=60.0) as client:
            async with client.stream(
                "POST",
                api_url,
                headers={
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": model,
                    "messages": messages,
                    "stream": True,
                    "max_tokens": 1024,
                },
            ) as response:
                if response.status_code != 200:
                    yield f'data: {{"error": "API error: {response.status_code}"}}\n\n'
                    return

                async for line in response.aiter_lines():
                    if line.startswith("data: "):
                        data = line[6:]
                        if data == "[DONE]":
                            yield "data: [DONE]\n\n"
                            return
                        try:
                            chunk = json.loads(data)
                            content = chunk.get("choices", [{}])[0].get("delta", {}).get("content", "")
                            if content:
                                yield f"data: {json.dumps({'content': content})}\n\n"
                        except json.JSONDecodeError:
                            continue
    except httpx.ConnectError:
        yield 'data: {"error": "Cannot connect to LLM API. Check your API URL."}\n\n'
    except Exception as e:
        yield f'data: {{"error": "{str(e)}"}}\n\n'


async def call_llm_json(prompt: str, settings: dict) -> dict:
    """Call LLM with a prompt that requests JSON output. Returns parsed dict.

    Raises ValueError if LLM returns non-JSON or if API key is missing.
    """
    api_key = settings.get("llm_api_key", "")
    api_url = settings.get("llm_api_url", "https://api.deepseek.com/v1/chat/completions")
    model = settings.get("llm_model", "deepseek-chat")

    if not api_key:
        raise ValueError("LLM API key not configured")

    messages = [
        {"role": "system", "content": SYSTEM_PROMPT + "\n\nYou MUST respond with valid JSON only. No markdown, no explanation, just the JSON object."},
        {"role": "user", "content": prompt},
    ]

    async with httpx.AsyncClient(timeout=60.0) as client:
        resp = await client.post(
            api_url,
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
            json={
                "model": model,
                "messages": messages,
                "max_tokens": 1024,
                "temperature": 0.3,
            },
        )

    if resp.status_code != 200:
        raise ValueError(f"LLM API error: {resp.status_code} {resp.text[:200]}")

    content = resp.json()["choices"][0]["message"]["content"]

    # Strip markdown code fences if present
    content = re.sub(r"```json\s*", "", content)
    content = re.sub(r"```\s*", "", content)
    content = content.strip()

    return json.loads(content)


def build_action_prompt(action: str, word_data: dict) -> str:
    """Build the structured prompt for a quick action."""
    word = word_data["word"]
    pos = word_data.get("pos", "")
    meaning_cn = word_data.get("meaning_cn", "")
    template = ACTION_PROMPTS.get(action, ACTION_PROMPTS["examples"])
    return template.format(word=word, pos=pos, meaning_cn=meaning_cn)
