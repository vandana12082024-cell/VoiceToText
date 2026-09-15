import os
import httpx
import pytest

os.environ.update({"DATABASE_URL": "postgresql+asyncpg://localhost/test", "SUPABASE_URL": "https://example.supabase.co", "SUPABASE_ANON_KEY": "public", "SUPABASE_JWT_ISSUER": "https://example.supabase.co/auth/v1", "GROQ_API_KEY": "test", "GROQ_LLM_MODEL": "test-model"})

from app.providers import GroqProvider, ProviderError


@pytest.mark.asyncio
async def test_transcription_keeps_language_detection_for_mixed_speech():
    async def handler(request):
        assert b'language' not in request.content
        return httpx.Response(200, json={"text": "Kal meeting hai at 5."})
    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        text = await GroqProvider(client).transcribe(b"audio", "sample.m4a", "audio/mp4", "hinglish")
    assert text == "Kal meeting hai at 5."


@pytest.mark.asyncio
async def test_empty_transcript_is_rejected():
    async with httpx.AsyncClient(transport=httpx.MockTransport(lambda _: httpx.Response(200, json={"text": "  "}))) as client:
        with pytest.raises(ProviderError):
            await GroqProvider(client).transcribe(b"audio", "sample.m4a", "audio/mp4", "auto")


@pytest.mark.asyncio
async def test_rewrite_prompt_preserves_facts():
    async def handler(request):
        body = __import__("json").loads(request.content)
        prompt = body["messages"][0]["content"]
        assert "names, numbers, dates, URLs" in prompt
        assert body["messages"][1]["content"] == "Meet Asha at 5 on example.com"
        return httpx.Response(200, json={"choices": [{"message": {"content": "Please meet Asha at 5 on example.com."}}]})
    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        result = await GroqProvider(client).rewrite("Meet Asha at 5 on example.com", "en", "formal")
    assert result == "Please meet Asha at 5 on example.com."
