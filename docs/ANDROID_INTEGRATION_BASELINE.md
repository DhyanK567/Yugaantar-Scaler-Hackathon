# M28 — Android Integration Baseline

**Project:** MediLocker (GuptKavach / Raksha Engine)  
**Track:** Yugaantar DevForge — Track 3: Secret Wards (Offline, CPU-only, Zero-LLM)  
**Tagline:** *Protect the Identity. Preserve the Medicine. Enable Collaboration.*

---

## 1. Architecture Stack Discovered

| Layer | Technology / Version | Location | Role |
|---|---|---|---|
| **Android Shell** | Kotlin `2.0.21`, AGP `8.7.3`, `compileSdk 36`, `minSdk 26`, `targetSdk 36` | `android/app/` | `MainActivity.kt` hosts a restricted `WebView` (`127.0.0.1` / `localhost` only) |
| **Local HTTP Bridge** | NanoHTTPD `2.3.1` | `android/app/src/main/java/org/medilocker/privacy/LocalApiServer.kt` | Loopback-only (`127.0.0.1:8000`) static & `/api/*` server |
| **In-Process Python** | Chaquopy `16.0.0` (CPython `3.11`) | `android/app/src/main/python/android_api_bridge.py` | Executes API routing, SQLite persistence, and privacy engine in-process |
| **Privacy Engine** | Official GuptKavach / Raksha Engine | `starter/main.py`, `starter/verify_passport.py`, `starter/raksha_engine/*` | Same verified offline CPU-only engine used by the official CLI |
| **Frontend UI** | Next.js `16.4.6` + React `19.3.0` + Tailwind `4.3.3` (`output: "export"`) | `frontend/` → `android/app/src/main/assets/www/` | `22/22` static routes including all 12 dashboard modules |
| **Database** | SQLite (`medilocker.db`) in `context.filesDir` | `android_api_bridge.py` | Non-sensitive operational metadata, hashed sessions, assessments, passports, audit trail |
| **Signing** | External RSA-2048 JKS via env vars | `C:\Users\Dell\.medilocker\medilocker-release.jks` | APK Signature Scheme v2 (`apksigner` verified) |
| **Official Validators** | Python CLI contracts | `validate_output.py`, `check_dev.py`, `check_submission.py` | Verified `READY TO SUBMIT` (`CONTRACT OK`) |

---

## 2. Offline Engine Feasibility

- `starter/main.py` and `starter/raksha_engine/*` use pure Python + standard library + `PyYAML` (CPU-only, zero LLMs, zero external APIs, zero native desktop-only dependencies).
- Running in-process via Chaquopy inside `LocalApiServer.kt` eliminates subprocess spawning overhead and guarantees identical deterministic pseudonymisation (`engine_main.SECRET = raksha_secret.encode("utf-8")`) and sanitisation behavior as the official CLI.
