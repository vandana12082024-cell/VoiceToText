# Voice to Text mobile app

This repository contains a Flutter voice writing app and a FastAPI API. Supabase Auth signs users in; the API validates Supabase JWTs and stores preferences and transcripts in Supabase Postgres. The API calls Groq speech-to-text and Groq chat completions with server-side credentials. Raw transcription and rewriting are distinct user actions.

## Setup

To build an APK using Codemagic without installing Flutter, follow [Phone testing with cloud builds](docs/PHONE_TESTING.md).

1. Create a Supabase project with asymmetric JWT signing enabled. Copy the database connection URL, project URL and publishable key. Use the Supabase transaction pooler connection string if the API host cannot reach the direct IPv6 database endpoint. Keep the database password and Groq key on the backend.
2. Copy `backend/.env.example` to `backend/.env` and fill in the values. Set `GROQ_LLM_MODEL` to an available chat model. Set `DATABASE_URL` to an `postgresql+asyncpg://` URL.
3. Install Python 3.12+, then run `pip install -e '.[dev]'`, `alembic upgrade head`, and `uvicorn app.main:app --reload` from `backend/`. Docker users can run `docker compose up --build`. The container migrates the database before starting the API and uses `PORT` (default 8000). This startup arrangement is for a single test service; coordinate migrations separately before running multiple service replicas.
4. Install a Flutter SDK with Dart 3.13+. From `mobile/`, run `flutter create --platforms=android,ios .` to generate native platform scaffolding, then `flutter pub get`. Android needs `android.permission.RECORD_AUDIO` and `android.permission.INTERNET` in `AndroidManifest.xml`; iOS needs `NSMicrophoneUsageDescription` in `Info.plist`. Set Android minSdk to at least 23 as required by `record`.
5. Run `flutter run --dart-define=SUPABASE_URL=https://PROJECT.supabase.co --dart-define=SUPABASE_PUBLISHABLE_KEY=YOUR_PUBLIC_KEY --dart-define=API_BASE_URL=https://YOUR_API_HOST`. Use a reachable HTTPS API host for physical devices. A local emulator can use its host gateway during development.

`SUPABASE_PUBLISHABLE_KEY` is public. Never supply the Groq key or Supabase service-role key to Flutter.

## Implemented scope

Email/password sign-up and sign-in, language and tone settings, microphone recording, audio upload, transcription, rewrite, copy, history and delete are present. Audio is deleted from the mobile temp directory after upload and is never stored on the backend. Backend requests have a request ID and return a stable envelope.

Android floating overlays, native iOS keyboard extension, background workers, Supabase Storage retention, usage limits and subscriptions are future work. They need native platform projects, credentials and real-device validation. The current API uses a synchronous fast path and should be moved to jobs before accepting long recordings. `save_audio` is reserved in preferences but no audio retention is currently enabled.

## Verification

Run `python -m pytest` from `backend/`, then `flutter analyze` and `flutter test` from `mobile/` after installing Flutter. Device builds and live provider calls require configured services.
