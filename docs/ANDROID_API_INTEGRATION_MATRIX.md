# M28 — Android API Integration Matrix

All routes served locally over `http://127.0.0.1:8000` by `LocalApiServer.kt` → `android_api_bridge.py`.

| Endpoint | Method | Auth | Request | Success Response (`200`) | Failure Status | Android / Bridge Handler | Test Coverage |
|---|---|---|---|---|---|---|---|
| `/api/health` | `GET` | Public | — | `{"status":"healthy","mode":"android-offline-cpu",...}` | — | `android_api_bridge.py` | `test_unauthenticated_rejected_and_diagnostics_ok`, Live Emulator |
| `/api/auth/config` | `GET` | Public | — | `{"offline_mode":true,"dev_login_enabled":true,...}` | — | `android_api_bridge.py` | `android_api_bridge` E2E |
| `/api/auth/offline-demo` | `POST` | Public | `{}` | `{"user":...,"token":...}` + `Set-Cookie` | — | `android_api_bridge.py` | `test_android_bridge_comprehensive.py`, Live Emulator |
| `/api/auth/me` | `GET` | Cookie/Bearer | — | `{"user":...}` | `401` | `android_api_bridge.py` | `test_guptkavach_system.py` |
| `/api/dashboard/overview` | `GET` | Cookie/Bearer | — | `{"metrics":...,"privacy_health":...,"recent_jobs":...}` | `401` | `android_api_bridge.py` | Live Emulator, `android_api_bridge` E2E |
| `/api/organisations` | `GET`/`POST` | Cookie/Bearer | JSON org | Org list / created org | `400`/`401` | `android_api_bridge.py` | `android_api_bridge.py` |
| `/api/datasets` | `GET`/`POST` | Cookie/Bearer | `multipart/form-data` (`files`, `auto_process`) | Dataset list / `{"dataset_id":...,"job":...}` | `400`/`401` | `android_api_bridge.py` | `test_multiformat_hindi_filename_quarantine_and_zip_security`, Live Emulator |
| `/api/datasets/{id}` | `GET`/`DELETE` | Cookie/Bearer | — | Dataset + jobs / `{"status":"deleted"}` | `401`/`404` | `android_api_bridge.py` | `test_android_bridge_comprehensive.py` |
| `/api/datasets/process-sample` | `POST` | Cookie/Bearer | `{}` | `{"dataset_id":...,"job":...}` | `401` | `android_api_bridge.py` | `android_api_bridge` E2E |
| `/api/jobs` | `GET`/`POST` | Cookie/Bearer | `{"dataset_id":...}` | Job list / job summary | `401`/`404` | `android_api_bridge.py` | `test_android_bridge_comprehensive.py` |
| `/api/jobs/{id}`, `/events`, `/results` | `GET` | Cookie/Bearer | — | Job row / stage events / full assessment+passport bundle | `401`/`404` | `android_api_bridge.py` | `test_android_bridge_comprehensive.py` |
| `/api/jobs/{id}/download` | `GET` | Cookie/Bearer | — | `application/zip` (excludes `records.jsonl` & `quarantine/`) | `400`/`401`/`404` | `android_api_bridge.py` | `test_multiformat_hindi_filename_quarantine_and_zip_security` |
| `/api/quarantine` | `GET` | Cookie/Bearer | `?job_id=` | `{"status":...,"total_quarantined":...,"items":...}` | `401` | `android_api_bridge.py` | `test_android_bridge_comprehensive.py` |
| `/api/privacy-intelligence` | `GET` | Cookie/Bearer | — | Risk map & assessment summary | `401` | `android_api_bridge.py` | `test_android_bridge_comprehensive.py` |
| `/api/clinical/reports` | `GET` | Cookie/Bearer | — | Clinical drift & FHIR integrity reports | `401` | `android_api_bridge.py` | `test_android_bridge_comprehensive.py` |
| `/api/identity/clusters` | `GET` | Cookie/Bearer | `?job_id=` | Cluster & linking status (`precision: NOT_MEASURED`) | `401` | `android_api_bridge.py` | `test_android_bridge_comprehensive.py` |
| `/api/threat-lab`, `/api/attack-simulator/run` | `GET`/`POST` | Cookie/Bearer | — | Attack simulation & risk summary | `401` | `android_api_bridge.py` | `test_android_bridge_comprehensive.py` |
| `/api/passports`, `/{id}`, `/{id}/verify`, `/{id}/download` | `GET`/`POST` | Cookie/Bearer | `?format=json\|html` | Passport list, verification (`integrity_valid`), bundle | `401`/`404` | `android_api_bridge.py` | `test_android_bridge_comprehensive.py` |
| `/api/audit/events` | `GET` | Cookie/Bearer | — | Organisation audit trail (zero PII/secrets) | `401` | `android_api_bridge.py` | `test_android_bridge_comprehensive.py` |
| `/api/research/requests` (+ `approve`/`reject`) | `GET`/`POST` | Cookie/Bearer | JSON request | Research request CRUD | `401`/`404` | `android_api_bridge.py` | `android_api_bridge.py` |
| `/api/settings` | `GET`/`POST` | Cookie/Bearer | Policy bounds | Policy settings | `400`/`401` | `android_api_bridge.py` | `test_android_bridge_comprehensive.py` |
| `/api/system/diagnostics` | `GET` | Cookie/Bearer | — | `{"offline_mode":true,"cpu_only":true,"engine_loaded":true}` | `401` | `android_api_bridge.py` | `test_unauthenticated_rejected_and_diagnostics_ok` |
