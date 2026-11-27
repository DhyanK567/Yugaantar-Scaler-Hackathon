# MEDILOCKER M20 — ANDROID ARCHITECTURE & COMPATIBILITY AUDIT
**Date:** 2026-11-27  
**Auditor:** Principal Android Engineer & Python Runtime Architect  

---

## 1. Current Architecture

MediLocker currently consists of three layers:
1. **Frontend (`frontend/`)**: Next.js `16.4.6` + React `19.3.0` + Tailwind CSS `4.3.3` + `lucide-react`. Configured with `output: "export"`, `trailingSlash: true`, `images: { unoptimized: true }` in `frontend/next.config.ts`, producing a static HTML/JS/CSS bundle in `frontend/out/`.
2. **Backend (`backend/`)**: FastAPI + SQLite (`data/guptkavach.db`) + `google-auth` (`backend/auth.py`, `backend/main.py`, `backend/pipeline.py`, `backend/database.py`, `backend/engine_adapter.py`, `backend/audit.py`). Invokes `starter/main.py` via `subprocess.run`.
3. **Core Privacy Engine (`starter/main.py` + `starter/raksha_engine/`)**: Pure-Python two-pass deterministic privacy engine (`normalizer.py`, `evidence.py`, `names.py`, `patterns.py`, `linking.py`, `privacy.py`, `sanitizer.py`, `crypto.py`, `secure_fs.py`, `quarantine.py`, `attacker.py`, `risk_engine.py`, `mitigation.py`, `qi_classifier.py`, `privacy_utility.py`, `clinical_validator.py`, `passport.py`, `passport_report.py`). Runtime dependency: `cryptography>=41.0` (with pure-stdlib fallback in `crypto.py` and `UNSIGNED` fallback in `passport.py`).

---

## 2. Mobile Compatibility Issues

1. **Frontend API Base URL (`frontend/src/lib/api.ts`)**:
   - `getApiBase()` defaults to `http://${window.location.hostname}:8000` (which resolves to `http://localhost:8000` inside an Android WebView/Capacitor shell) and uses `credentials: "include"` cookies.
   - Inside an Android WebView loaded from `https://localhost` or `http://127.0.0.1:<port>`, cross-origin `SameSite=Lax` cookies between different ports/schemes can be blocked unless served from the **same local origin** or using `Authorization: Bearer <token>` header (which `backend/auth.py:477` ALREADY supports via `extract_session_token(cookie_token, authorization)`!).
2. **Backend Subprocess Spawning (`backend/engine_adapter.py`)**:
   - `subprocess.run([sys.executable, "starter/main.py", ...])` **cannot** run inside an Android app sandbox because `sys.executable` is not a standalone Python CLI binary on Android (`SELinux` / `noexec` `/data` restrictions).
   - **Solution**: Run `starter/main.py` / `raksha_engine` **in-process** via embedded CPython (**Chaquopy**) on Android!
3. **Desktop Dependencies (`google-auth`, `uvicorn`, `fastapi`)**:
   - Full `FastAPI` + `uvicorn` + `pydantic-core` (Rust native wheel) + `google-auth` can be heavy or lack prebuilt Android ARM64 wheels on Chaquopy.
   - By contrast, `starter/raksha_engine/` is **100% pure Python stdlib** (+ optional `cryptography` Chaquopy wheel), and Android's Kotlin/Java layer has native `java.net.ServerSocket` / `NanoHTTPD`-style lightweight HTTP server + `android.database.sqlite.SQLiteOpenHelper`!
4. **Mobile UI & Navigation (`frontend/src/components/layout/Sidebar.tsx`)**:
   - Desktop fixed sidebar (`w-64`) needs responsive mobile drawer / bottom-bar support, touch-friendly controls, Android back-button handling, and native file picker / download / PDF sharing hooks.

---

## 3. Existing Features & Dependencies Evaluated

| Component | Android Feasibility | Notes |
| :--- | :--- | :--- |
| **Next.js Static Export (`frontend/out`)** | **Fully Feasible** | `next.config.ts` already uses `output: "export"`. |
| **Core Privacy Engine (`starter/raksha_engine`)** | **Fully Feasible (Offline)** | Pure Python; runs in-process via Chaquopy (`arm64-v8a`, `x86_64`). |
| **SQLite Persistence** | **Fully Feasible (Offline)** | Native Android `SQLiteDatabase` / Python `sqlite3` in `context.filesDir`. |
| **Cryptographic Assurance (`crypto.py`, `privacy.py`)** | **Fully Feasible (Offline)** | HKDF-SHA256 & HMAC-SHA256 use stdlib `hashlib`/`hmac`; AEAD uses `cryptography` or stdlib `HMAC-SHA256-CTR`. |
| **Clinical Drift, Attack Sim, Passport** | **Fully Feasible (Offline)** | `clinical_validator.py`, `attacker.py`, `passport.py`, `verify_passport.py` are pure Python. |
| **Google OAuth / SMTP OTP** | **Network-Optional / Desktop-Only** | Offline Android mode uses local Android Keystore-backed session + `/api/auth/offline-demo` / local PIN/auth. |

---

## 4. Offline Processing Feasibility

**100% Feasible** using **Option D (Hybrid Native Android Shell + Static Next.js UI + Embedded Chaquopy CPython Engine)**:
- The Android app starts an embedded `127.0.0.1` loopback HTTP server (bound strictly to `127.0.0.1` on an ephemeral/local port `8000` or `18432`) serving both the static `frontend/out/` assets (same-origin, so `HttpOnly` cookies and `fetch()` work identically!) and the `/api/*` REST endpoints backed by Android SQLite + Chaquopy in-process `starter/main.py` execution!
- Zero network permissions needed for privacy processing (`ACCESS_NETWORK_STATE` only for offline status indicator; no `INTERNET` required for core engine, or `INTERNET` only if user explicitly connects to a remote server).

---

## 5. Recommended Android Packaging Strategy

- **Directory**: `android/` (Gradle Android project, `applicationId "org.medilocker.privacy"`, `minSdk 26`, `targetSdk 36`, `compileSdk 36`).
- **ABIs**: `arm64-v8a` and `x86_64` (covers modern physical Android phones and Android Studio x86_64 emulators).
- **Embedded Python**: Chaquopy (`com.chaquo.python`) bundling `starter/main.py`, `starter/verify_passport.py`, `starter/config/policy.yaml`, and `starter/raksha_engine/*`.
- **Frontend Assets**: `frontend/out/` copied into `android/app/src/main/assets/www/` during build.
- **Local Loopback Bridge**: Kotlin `LocalApiServer` bound to `127.0.0.1:8000` (with fallback port) + `MainActivity` `WebView` with `WebChromeClient.onShowFileChooser` (native Android file picker), `DownloadListener` (Android `FileProvider` / `MediaStore` export), `BackPressedCallback` (history back navigation), and `android:allowBackup="false"`.

---

## 6. Security Limitations

1. **APK Signing**: No pre-existing release keystore is present in the workspace (`keytool` is not on PATH; `JDK 25` is installed). If a release keystore is not provided externally, a local debug/test-signed or clearly documented local-keystore-signed APK must be generated without committing keystores to Git.
2. **Android Keystore vs `RAKSHA_SECRET`**: `RAKSHA_SECRET` is never embedded in the APK; it is generated/stored at runtime in Android `EncryptedSharedPreferences` / Android Keystore or user-supplied per-session.
3. **Physical Device / Emulator Availability**: `C:\Users\Dell\AppData\Local\Android\Sdk` is present (`platforms/android-36`, `build-tools/35.0.0` & `36.1.0`, `system-images/android-36.1`), but `AVDs -> NONE`. Emulator creation & launch will be attempted; if hardware virtualization/network blocks Gradle/AVD, exact blockers will be documented without falsifying results.

---

## 7. Required Code Changes

1. `frontend/`: Ensure mobile-responsive drawer/bottom navigation in `Sidebar.tsx`, offline status indicator, and `frontend/out/` static export build.
2. `android/`: Create complete Gradle Android project (`settings.gradle.kts`, `build.gradle.kts`, `app/build.gradle.kts`, `AndroidManifest.xml`, `MainActivity.kt`, `LocalApiServer.kt`, `PythonEngineBridge.kt`, `res/xml/file_paths.xml`, `res/xml/backup_rules.xml`).
3. `docs/M20_TEST_INVENTORY.md` & `scripts/security_regression_gate.py`: Discover and run all repository test suites.

---

## 8. Build Risks

1. **JDK 25 vs Gradle/AGP/Chaquopy Compatibility**: The host has `JDK 25` (`C:\Program Files\Java\jdk-25`), and `gradle` is not pre-installed globally. AGP 8.x / Chaquopy may fail on JDK 25 unless Gradle 9.x or JDK 17/21 is used. We will test this directly when initializing the Gradle wrapper.
2. **Offline / Network Dependencies**: Downloading Gradle wrapper / Maven artifacts (AGP, Chaquopy) requires network access during the build step, though the resulting APK runs 100% offline.
