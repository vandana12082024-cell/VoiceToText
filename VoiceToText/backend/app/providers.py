from typing import Protocol
import httpx
from app.config import settings

BASE_URL = "https://api.groq.com/openai/v1"


class SpeechProvider(Protocol):
    async def transcribe(self, audio: bytes, filename: str, content_type: str, language: str) -> str: ...


class LLMProvider(Protocol):
    async def rewrite(self, text: str, language: str, tone: str) -> str: ...


class ProviderError(Exception):
    pass


class GroqProvider:
    def __init__(self, client: httpx.AsyncClient):
        self.client = client

    def _headers(self) -> dict[str, str]:
        return {"Authorization": f"Bearer {settings().groq_api_key}"}

    async def transcribe(self, audio: bytes, filename: str, content_type: str, language: str) -> str:
        data = {"model": settings().groq_stt_model, "response_format": "json"}
        if language in ("en", "hi", "ta", "kn", "ml"):
            data["language"] = language
        try:
            response = await self.client.post(f"{BASE_URL}/audio/transcriptions", headers=self._headers(), data=data, files={"file": (filename, audio, content_type)})
            response.raise_for_status()
            text = response.json().get("text", "").strip()
            if not text:
                raise ProviderError("Empty transcript")
            return text
        except (httpx.HTTPError, ValueError, KeyError) as exc:
            raise ProviderError("Speech provider failed") from exc

    async def rewrite(self, text: str, language: str, tone: str) -> str:
        prompt = ("You are a writing assistant. Rewrite only the user's text in the requested tone and output language. "
                  "Preserve meaning, intent, names, numbers, dates, URLs, product names and technical terms. "
                  "Do not invent facts. Output only the rewritten text. "
                  f"Tone: {tone}. Output language: {language}; auto means preserve the input language and code mixing.")
        try:
            response = await self.client.post(f"{BASE_URL}/chat/completions", headers=self._headers(), json={"model": settings().groq_llm_model, "temperature": 0.2, "messages": [{"role": "system", "content": prompt}, {"role": "user", "content": text}]})
            response.raise_for_status()
            result = response.json()["choices"][0]["message"]["content"].strip()
            if not result:
                raise ProviderError("Empty rewrite")
            return result
        except (httpx.HTTPError, ValueError, KeyError, IndexError, TypeError) as exc:
            raise ProviderError("Language provider failed") from exc
