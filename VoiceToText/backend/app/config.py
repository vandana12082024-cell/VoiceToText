from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")
    database_url: str
    supabase_url: str
    supabase_anon_key: str
    supabase_jwt_issuer: str
    groq_api_key: str
    groq_stt_model: str = "whisper-large-v3-turbo"
    groq_llm_model: str
    max_audio_bytes: int = 26_214_400
    groq_timeout_seconds: float = 45


@lru_cache
def settings() -> Settings:
    return Settings()
