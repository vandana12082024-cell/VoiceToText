# Test on Android without installing Flutter

Codemagic builds the APK. A separate hosted FastAPI service runs the API. Supabase supplies authentication and Postgres, and Groq supplies speech recognition and rewriting. The phone needs an internet connection; this method does not use USB debugging or your PC's localhost.

The cloud workflow is provided in `codemagic.yaml`. Its Android preparation script generates native Android scaffolding on the builder, adds microphone/internet permissions and keeps the application's Dart source. It produces a debug APK for initial device testing. It has not yet been built successfully on Codemagic or tested on a physical phone.

## 1. Update the private GitHub repository

Commit/upload the updated project, including the root `codemagic.yaml`, `scripts/`, `mobile/` and `backend/`. Keep the folder layout. Never upload `backend/.env`, virtual environments or private keys. If using GitHub's file-upload UI, upload the project contents so `codemagic.yaml` appears at the repository root beside `mobile` and `backend`, not inside another VoiceToText folder.

## 2. Host the API (example: Render)

If you already have a working public HTTPS API URL, use it and skip creating another service.

In Render, create a Web Service from the private GitHub repository and set:

| Setting | Value |
| --- | --- |
| Root Directory | `backend` |
| Language/runtime | Docker |
| Dockerfile Path | `./Dockerfile` |
| Docker Build Context | `.` (relative to Root Directory) |
| Health Check Path | `/health` |

Leave Docker Command empty: the Dockerfile runs `start.py`, which creates/updates tables and starts the API on Render's `PORT`.

Add these as environment variables in the backend hosting dashboard, using values from your local backend configuration:

```
DATABASE_URL
SUPABASE_URL
SUPABASE_ANON_KEY
SUPABASE_JWT_ISSUER
GROQ_API_KEY
GROQ_STT_MODEL
GROQ_LLM_MODEL
MAX_AUDIO_BYTES
GROQ_TIMEOUT_SECONDS
```

Use the Supabase session pooler connection string with a `postgresql+asyncpg://` prefix. URL-encode reserved characters in the database password. Set JWT issuer to the project URL followed by `/auth/v1`. Supabase signing must use ES256 or RS256 for the current backend. `SUPABASE_ANON_KEY` is a legacy-named required configuration field; the app's Supabase publishable key can be used for it in this version.

Deploy the service. Open the resulting URL followed by `/health`, for example `https://your-voice-api.onrender.com/health`. It should return `{"status":"ok"}`. This verifies API startup, not Groq access. Keep the service available while testing; a sleeping instance can cause an initial mobile timeout, so open the health URL first and wait until it responds.

## 3. Configure the mobile build

In your Codemagic application's **Environment variables** tab, create the group named exactly `mobile_config`. Add:

| Name | Value |
| --- | --- |
| `API_BASE_URL` | Public HTTPS backend origin, such as `https://your-voice-api.onrender.com` |
| `SUPABASE_URL` | `https://YOUR_PROJECT.supabase.co` |
| `SUPABASE_PUBLISHABLE_KEY` | The project's public publishable key |

Do not append `/api/v1` or `/health` to `API_BASE_URL`: the mobile repository adds its API prefix. Do not put the Groq key, database password or Supabase secret/service-role key in these mobile build settings. Values passed with `--dart-define` are included in the installed app.

## 4. Build the APK

In Codemagic, select the branch containing the updated files. If necessary, click **Check for configuration file** to detect the root `codemagic.yaml`. Click **Start new build**, select the workflow **Android test APK** (ID `android-test`) and start it.

The build runs setup helper tests, validates public configuration, generates the Android platform, installs packages, analyzes app source and runs `flutter build apk --debug`. A Dart SDK meeting `mobile/pubspec.yaml` is required; the workflow uses Flutter stable.

When the build succeeds, download `app-debug.apk` from its artifacts. The artifact's source path is `mobile/build/app/outputs/flutter-apk/app-debug.apk`. An `.aab` file cannot be installed directly in the same way.

## 5. Install and test

Open Codemagic in your Android phone's browser and download the APK, or transfer the downloaded APK from your PC. Open it using Downloads/Files, allow installation from that browser or file manager when Android prompts, and install. Launch **Voice to Text**.

Sign up and confirm your email if required, sign in, choose language/tone in Settings, and record a short sample. Allow microphone access. Stop, review the transcript, tap Polish text, copy the output and check History/delete.

Rebuild the APK after changing Flutter code or the three mobile build variables. Restart/redeploy the API after changing backend configuration; a Groq key change alone does not require rebuilding the APK. Cloud debug builds can use different signing keys: if Android rejects an update because of a signature conflict, uninstall the previous test app before installing the new APK (this clears local app data). Use a stable signing key for regular distribution.

## Troubleshooting

| Symptom | Next check |
| --- | --- |
| Codemagic cannot find a workflow | Confirm `codemagic.yaml` is committed at the selected branch's repository root. |
| Missing variable/group | Create `mobile_config` in the app's Environment variables tab and add all three values. |
| No APK artifact | Open the first failed build step; an APK is only produced after compilation succeeds. |
| API cannot deploy | Check migration/connection errors and database URL before attempting another mobile build. |
| Request timeout | Open the hosted `/health` URL, wait for a response, then retry in the app. |
| API returns 401 | Confirm the Supabase project/issuer/signing algorithm; sign out and back in. |
| Speech/rewriting fails | Verify Groq credentials, model availability and limits in the backend configuration. |

Do not publish this starter as a production app based only on a successful build. Overlay recording, iOS keyboard, quotas and background processing are not implemented.

References: [Codemagic Flutter builds](https://docs.codemagic.io/yaml-quick-start/building-a-flutter-app/), [Codemagic variable groups](https://docs.codemagic.io/yaml-basic-configuration/configuring-environment-variables/), [Render Docker services](https://render.com/docs/docker).
