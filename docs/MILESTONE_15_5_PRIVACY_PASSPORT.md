# MEDILOCKER — MILESTONE 15.5 VERIFIABLE PRIVACY PASSPORT
**Phase 4 Specification & Verification**

---

## 1. Live Passport Generation & Verification Architecture

1. **Canonical Generation (`starter/raksha_engine/passport.py`)**:
   - Every pipeline execution emits `dataset_manifest.json` (streaming SHA-256 of every file under `sanitized/`), `privacy_passport.json`, and `privacy_passport.html`.
   - Includes `certificate_identity` (ID, schema version, engine version, timestamp), `dataset_provenance` (input fingerprint, output manifest root hash), `privacy_assessment`, `identity_assessment`, `clinical_integrity`, `security_assessment`, `release_decision`, and `signature` (`Ed25519` when configured, otherwise `UNSIGNED`).
   - Enforces `assert_no_sensitive_data()` before writing so raw PII, canary strings, and `RAKSHA_SECRET` can never enter any passport artifact.
2. **Backend Integration (`backend/pipeline.py`, `backend/main.py`)**:
   - `backend/pipeline.py` ingests `privacy_passport.json` and `output_manifest_root_hash` directly into the `passports` table.
   - `POST /api/passports/{passport_id}/verify` invokes `verify_passport_bundle()` (`starter/verify_passport.py`), recomputing the streaming SHA-256 manifest across all sanitized files on disk and validating the root hash, schema, expiry, and Ed25519 signature.
   - Any altered output file or tampered passport JSON immediately returns `integrity_valid: false` and status `TAMPERED`.
