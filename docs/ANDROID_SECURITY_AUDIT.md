# M28 — Android Security Audit

## 1. Controls Implemented & Verified

| Control | Implementation | Verification |
|---|---|---|
| **`RAKSHA_SECRET` Protection** | Generated per-device (256-bit `SecureRandom`) in Android `SharedPreferences` (`MODE_PRIVATE`), injected at runtime into `engine_main.SECRET`; never embedded in APK assets or SQLite | `ZERO_RAW_PII_IN_DB_OK` + `test_multiformat_hindi_filename_quarantine_and_zip_security` |
| **Unauthenticated Access Rejection** | Session cookie (`medilocker_session`, `HttpOnly; SameSite=Lax`) required on all non-public `/api/*` routes; returns `401` otherwise | `test_unauthenticated_rejected_and_diagnostics_ok` + `test_guptkavach_system.py` |
| **No `records.jsonl` / `quarantine/` Exposure** | `GET /api/jobs/{id}/download` explicitly skips `records.jsonl` and `quarantine/*` when building the output ZIP, and enforces `organisation_id` ownership | `test_multiformat_hindi_filename_quarantine_and_zip_security` |
| **Path Traversal Prevention** | `LocalApiServer.serveStaticAsset` rejects `..` (`400 Bad Request`); `android_api_bridge.py` validates `jid` against `^[A-Za-z0-9_.-]+$` and strips directory components from uploaded filenames | `LocalApiServerTest` + `test_multiformat_hindi_filename_quarantine_and_zip_security` |
| **WebView Hardening** | `allowFileAccess = false`, `mixedContentMode = MIXED_CONTENT_NEVER_ALLOW`, external URL navigation blocked (`host != "127.0.0.1" && host != "localhost"`) | `MainActivity.kt` + `LocalApiServerTest` |
| **Backup Exclusion** | `backup_rules.xml` and `data_extraction_rules.xml` exclude local app storage from Android Auto Backup | `AndroidManifest.xml` |
| **Network Security Config** | Cleartext HTTP permitted only for `127.0.0.1` / `localhost` loopback | `network_security_config.xml` |
| **Security Regression Gate** | `python scripts/security_regression_gate.py` | **10 / 10 gates PASSED** |
