# M20 — Android Security Report

**Application:** `org.medilocker.privacy` (`1.0.0-m20`)  
**Compliance Target:** Yugaantar DevForge Track 3 — Secret Wards (Offline, CPU-only, Zero-LLM, Zero-PII-Leakage)

---

## 1. Cryptographic & Secret Hygiene

- **No Embedded `RAKSHA_SECRET`:** Neither the source tree nor the compiled APK contains a hardcoded `RAKSHA_SECRET`. At first launch, `MainActivity.kt` generates a 256-bit cryptographically random secret stored in `EncryptedSharedPreferences` (Android Keystore-backed) and passes it to `init_android_runtime(files_dir, raksha_secret)`, which sets both `os.environ["RAKSHA_SECRET"]` and `engine_main.SECRET`.
- **Release Keystore Isolation:** Signing uses an external keystore (`C:\Users\Dell\.medilocker\medilocker-release.jks`) supplied via environment variables (`MEDILOCKER_KEYSTORE_PATH`, `MEDILOCKER_KEYSTORE_PASSWORD`, `MEDILOCKER_KEY_ALIAS`, `MEDILOCKER_KEY_PASSWORD`). `.gitignore` excludes `*.jks`, `*.keystore`, `android/local.properties`, `android/.gradle/`, and `android/app/build/`.
- **APK Signature:** Verified with `apksigner.bat` using APK Signature Scheme v2 (RSA-2048).

## 2. Network & WebView Isolation

- **Loopback-Only Local API:** `LocalApiServer.kt` binds NanoHTTPD exclusively to `127.0.0.1`, preventing LAN or external network exposure of the local privacy API.
- **Cleartext Policy:** `res/xml/network_security_config.xml` restricts cleartext traffic strictly to `127.0.0.1` / `localhost` for the local loopback bridge while disallowing cleartext traffic to external domains.
- **Offline Enforcement:** `init_android_runtime` sets `MEDILOCKER_OFFLINE_MODE="true"`. No LLMs, hosted AI APIs, or external model downloads exist in the pipeline.

## 3. Data Privacy & Persistence Controls

- **Unauthenticated Rejection:** Both `test_guptkavach_system.py` and `android_api_bridge.py` E2E verified HTTP `401` on protected endpoints without a valid session cookie.
- **Zero Raw PII in SQLite:** E2E inspection of `sqlite3.Connection.iterdump()` after processing a sample dataset confirmed zero raw patient names (`Aarav`, `Sharma`), phone numbers (`9876543210`), or `RAKSHA_SECRET` values are persisted in `medilocker.db`.
- **Cloud Backup Exclusion:** `res/xml/backup_rules.xml` and `res/xml/data_extraction_rules.xml` exclude sensitive local app storage from Android Auto Backup / device-to-device transfer.
- **Independent Privacy Benchmark:** `tests/independent_eval/run_independent_eval.py` verified `0/10` PII leaked, `0/2` canaries leaked, `36/36 (100.0%)` clinical fidelity, and `1/5` quarantined (`PASS`).
