# MEDILOCKER M23 — SECURITY AUDIT

**Date:** 2026-11-27

---

## Security Controls Verified

1. **Stale Cookie Hijack Prevention:** `get_current_user_optional()` ignores stale `medilocker_session` cookies when `is_judge_mode()` is `True`, preventing a prior `RESEARCHER` session from leaking into Judge Mode.
2. **Production Fail-Closed Guard:** `MEDILOCKER_ENV=production` unconditionally overrides `MEDILOCKER_MODE=judge` to `"organisation"`.
3. **Upload & Path Traversal Protection:** `upload_dataset` enforces `ALLOWED_UPLOAD_EXTENSIONS`, non-empty files, `25 MB` per-file / `100 MB` total caps (`413`), `sanitize_filename()` traversal stripping, and cleans up partial directories on failure.
4. **Restricted Mapping Isolation:** `records.jsonl` is excluded from default ZIP downloads and blocked (`403`) on `/api/jobs/{id}/mapping` in Judge Mode.
5. **No Secret / PII Exposure:** `RAKSHA_SECRET` is never exposed to frontend JS, logs, or PDF metadata.
