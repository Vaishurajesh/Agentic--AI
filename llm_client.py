"""
Thin wrapper around a free LLM provider (Groq's OpenAI-compatible API).

Design notes
------------
- Uses plain `requests` so no extra SDK dependency is required.
- Retries transient failures (timeouts / 5xx / rate limits) with backoff.
- If no API key is configured, or every retry fails, the client raises
  LLMUnavailableError so the caller (planner.py) can fall back to a
  deterministic offline template. This keeps the whole app demoable
  even with zero API credits.
"""
import os
import json
import time
import requests

GROQ_URL = "https://api.groq.com/openai/v1/chat/completions"


class LLMUnavailableError(Exception):
    pass


class LLMClient:
    def __init__(self):
        self.api_key = os.getenv("GROQ_API_KEY")
        self.model = os.getenv("GROQ_MODEL", "llama-3.1-8b-instant")
        self.max_retries = 3
        self.timeout = 30

    @property
    def is_configured(self) -> bool:
        return bool(self.api_key)

    def chat(self, system_prompt: str, user_prompt: str, json_mode: bool = False) -> str:
        """Call the LLM and return the raw text content of the reply."""
        if not self.is_configured:
            raise LLMUnavailableError("GROQ_API_KEY not set")

        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            "temperature": 0.3,
            "max_tokens": 1500,
        }
        if json_mode:
            payload["response_format"] = {"type": "json_object"}

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

        last_err = None
        for attempt in range(1, self.max_retries + 1):
            try:
                resp = requests.post(GROQ_URL, headers=headers, json=payload, timeout=self.timeout)
                if resp.status_code == 429 or resp.status_code >= 500:
                    # rate limited / server error -> retry with backoff
                    last_err = f"HTTP {resp.status_code}: {resp.text[:200]}"
                    time.sleep(1.5 * attempt)
                    continue
                resp.raise_for_status()
                data = resp.json()
                return data["choices"][0]["message"]["content"]
            except (requests.RequestException, KeyError, ValueError) as e:
                last_err = str(e)
                time.sleep(1.0 * attempt)

        raise LLMUnavailableError(f"Groq call failed after {self.max_retries} attempts: {last_err}")

    def chat_json(self, system_prompt: str, user_prompt: str) -> dict:
        """Call the LLM expecting a JSON object back; parse defensively."""
        raw = self.chat(system_prompt, user_prompt, json_mode=True)
        try:
            return json.loads(raw)
        except json.JSONDecodeError:
            # Some models wrap JSON in markdown fences despite instructions
            cleaned = raw.strip().strip("`")
            if cleaned.lower().startswith("json"):
                cleaned = cleaned[4:]
            return json.loads(cleaned)
