import uuid
from contextlib import asynccontextmanager
from datetime import datetime, timezone
import httpx
from fastapi import Depends, FastAPI, File, Form, HTTPException, Request, UploadFile
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from sqlalchemy import select, delete
from sqlalchemy.ext.asyncio import AsyncSession
from app.auth import current_user
from app.config import settings
from app.db import session
from app.models import Preference, Transcription
from app.providers import GroqProvider, ProviderError

LANGUAGES = {"auto", "en", "hi", "hinglish", "ta", "tanglish", "kn", "kanglish", "ml", "manglish"}
TONES = {"natural", "casual", "formal", "professional", "short"}
MIME_TYPES = {"audio/mp4", "audio/x-m4a", "audio/m4a", "audio/wav", "audio/x-wav", "audio/mpeg", "audio/ogg", "audio/webm", "audio/flac"}


@asynccontextmanager
async def lifespan(app: FastAPI):
    async with httpx.AsyncClient(timeout=settings().groq_timeout_seconds) as client:
        app.state.provider = GroqProvider(client)
        yield


app = FastAPI(title="Voice to Text API", lifespan=lifespan)


@app.middleware("http")
async def request_id(request: Request, call_next):
    request.state.request_id = str(uuid.uuid4())
    response = await call_next(request)
    response.headers["X-Request-ID"] = request.state.request_id
    return response


def ok(request: Request, data: object) -> dict:
    return {"success": True, "data": data, "error": None, "request_id": request.state.request_id}


@app.exception_handler(HTTPException)
async def http_error(request: Request, exc: HTTPException):
    return JSONResponse(status_code=exc.status_code, content={"success": False, "data": None, "error": {"code": "REQUEST_FAILED", "message": exc.detail}, "request_id": request.state.request_id})


@app.get("/health")
async def health():
    return {"status": "ok"}


class PreferenceInput(BaseModel):
    default_language: str = "auto"
    default_tone: str = "natural"
    auto_detect_language: bool = True
    save_audio: bool = False


class RewriteInput(BaseModel):
    transcription_id: uuid.UUID
    language: str = "auto"
    tone: str = "natural"


def preference_data(row: Preference) -> dict:
    return {"default_language": row.default_language, "default_tone": row.default_tone, "auto_detect_language": row.auto_detect_language, "save_audio": row.save_audio}


def transcription_data(row: Transcription) -> dict:
    return {"id": str(row.id), "raw_text": row.raw_text, "processed_text": row.processed_text, "language": row.language, "tone": row.tone, "created_at": row.created_at.isoformat()}


@app.get("/api/v1/preferences")
async def get_preferences(request: Request, user: uuid.UUID = Depends(current_user), db: AsyncSession = Depends(session)):
    row = await db.get(Preference, user)
    return ok(request, preference_data(row) if row else PreferenceInput().model_dump())


@app.patch("/api/v1/preferences")
async def update_preferences(request: Request, body: PreferenceInput, user: uuid.UUID = Depends(current_user), db: AsyncSession = Depends(session)):
    if body.default_language not in LANGUAGES or body.default_tone not in TONES:
        raise HTTPException(422, "Unsupported language or tone")
    row = await db.get(Preference, user)
    if row is None:
        row = Preference(user_id=user)
        db.add(row)
    for key, value in body.model_dump().items():
        setattr(row, key, value)
    row.updated_at = datetime.now(timezone.utc)
    await db.commit()
    return ok(request, preference_data(row))


@app.post("/api/v1/transcriptions")
async def transcribe(request: Request, audio: UploadFile = File(...), language: str = Form("auto"), tone: str = Form("natural"), user: uuid.UUID = Depends(current_user), db: AsyncSession = Depends(session)):
    if language not in LANGUAGES or tone not in TONES:
        raise HTTPException(422, "Unsupported language or tone")
    if audio.content_type not in MIME_TYPES:
        raise HTTPException(415, "Unsupported audio format")
    payload = await audio.read(settings().max_audio_bytes + 1)
    if not payload or len(payload) > settings().max_audio_bytes:
        raise HTTPException(413, "Audio is empty or too large")
    try:
        raw_text = await request.app.state.provider.transcribe(payload, audio.filename or "recording.m4a", audio.content_type, language)
    except ProviderError as exc:
        raise HTTPException(502, "Unable to transcribe audio") from exc
    row = Transcription(user_id=user, raw_text=raw_text, processed_text=None, language=language, tone=tone, stt_model=settings().groq_stt_model)
    db.add(row)
    await db.commit()
    await db.refresh(row)
    return ok(request, transcription_data(row))


@app.post("/api/v1/rewrite")
async def rewrite(request: Request, body: RewriteInput, user: uuid.UUID = Depends(current_user), db: AsyncSession = Depends(session)):
    if body.language not in LANGUAGES or body.tone not in TONES:
        raise HTTPException(422, "Unsupported language or tone")
    row = await db.get(Transcription, body.transcription_id)
    if row is None or row.user_id != user:
        raise HTTPException(404, "Transcript not found")
    try:
        row.processed_text = await request.app.state.provider.rewrite(row.raw_text, body.language, body.tone)
    except ProviderError as exc:
        raise HTTPException(502, "Unable to rewrite text") from exc
    row.language, row.tone, row.llm_model = body.language, body.tone, settings().groq_llm_model
    await db.commit()
    return ok(request, transcription_data(row))


@app.get("/api/v1/history")
async def history(request: Request, user: uuid.UUID = Depends(current_user), db: AsyncSession = Depends(session)):
    rows = (await db.scalars(select(Transcription).where(Transcription.user_id == user).order_by(Transcription.created_at.desc()).limit(50))).all()
    return ok(request, [transcription_data(row) for row in rows])


@app.delete("/api/v1/history/{item_id}")
async def remove_history(request: Request, item_id: uuid.UUID, user: uuid.UUID = Depends(current_user), db: AsyncSession = Depends(session)):
    result = await db.execute(delete(Transcription).where(Transcription.id == item_id, Transcription.user_id == user))
    await db.commit()
    if result.rowcount == 0:
        raise HTTPException(404, "Transcript not found")
    return ok(request, {"deleted": True})
