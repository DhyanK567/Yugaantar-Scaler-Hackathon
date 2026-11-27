# M28 — Android Offline Validation

## 1. Offline Architecture Verification

- **No External Network Dependencies:** No LLMs, generative APIs, cloud databases, or remote model downloads are used anywhere in the Android app or privacy engine.
- **Loopback-Only Execution:** `LocalApiServer.kt` binds NanoHTTPD strictly to `127.0.0.1:8000`. `MainActivity.kt` restricts `WebViewClient.shouldOverrideUrlLoading` to `127.0.0.1` / `localhost`.
- **In-Process Engine:** `Chaquopy 16.0.0` runs Python `3.11` and `starter/main.py` directly inside the Android process with `MEDILOCKER_OFFLINE_MODE="true"`.
- **Static UI Assets:** All `22/22` Next.js routes and `_next/static/chunks/*` are bundled inside `assets/www/` in the APK.

## 2. Verified Offline Flows

- **First Launch & Subsequent Launch:** Verified on `MediLocker_API36` (`android-36.1` `x86_64`) with `127.0.0.1:8000` serving `/dashboard/`, `/_next/static/chunks/2mlmic0sqyonj.css` (`HTTP 200`), and `/api/health` (`HTTP 200`, `mode: "android-offline-cpu"`).
- **Offline Demo Sign-In:** Verified `Sign in required` → `Continue in Offline Demo Mode` → `Privacy Dashboard` telemetry rendering.
- **Offline CSV Upload & Processing:** Verified `POST /api/datasets` with `dev/input/lab/city_results.csv` on the live emulator (`LIVE_ANDROID_UPLOAD_OK`).
