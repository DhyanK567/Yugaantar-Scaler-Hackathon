# MEDILOCKER M23 — API CONTRACT

| Method | Endpoint | Purpose | Auth / Mode Policy |
|---|---|---|---|
| `GET` | `/api/health` | Health & air-gapped engine status | Public |
| `GET` | `/api/auth/config` | Returns `mode`, `judge_mode`, `offline_mode`, `smtp_enabled`, `google_enabled` | Public |
| `GET` | `/api/auth/me` | Active user & workspace (`Local Evaluator` / `LOCAL_EVALUATOR` in Judge Mode) | `require_user` |
| `POST` | `/api/datasets` | Upload & validate synthetic files (`25 MB`/file, `100 MB` total); auto-runs pipeline | Judge: `LOCAL_EVALUATOR`; Org: `PLATFORM_ADMIN`, `ORG_ADMIN`, `PRIVACY_OFFICER` |
| `GET` | `/api/datasets` | List datasets scoped to workspace/org | `require_user` |
| `DELETE` | `/api/datasets/{id}` | Soft-delete dataset | Judge: `LOCAL_EVALUATOR`; Org: `PLATFORM_ADMIN`, `ORG_ADMIN`, `PRIVACY_OFFICER` |
| `GET` | `/api/jobs/{id}` | Job status, stage events & counts | `require_org_access` |
| `GET` | `/api/jobs/{id}/results` | Privacy, clinical, identity & passport payload | `require_org_access` |
| `GET` | `/api/jobs/{id}/download` | Sanitised bundle ZIP (`sanitized/`, `report.json`, `privacy_passport.json`) | `require_org_access` (`records.jsonl` excluded by default) |
| `GET` | `/api/jobs/{id}/report.json` | Processing `report.json` | `require_org_access` |
| `GET` | `/api/jobs/{id}/mapping` | Restricted `records.jsonl` patient mapping | **403 Blocked in Judge Mode**; Org: `PLATFORM_ADMIN`, `ORG_ADMIN`, `PRIVACY_OFFICER` |
| `GET` | `/api/jobs/{id}/privacy-report.pdf` | 3-page monochrome Privacy & Integrity Report PDF | `require_org_access` |
| `GET` | `/api/dashboard/metrics-summary` | Live 4-card metrics (`files_protected`, `identifiers_protected`, `clinical`, `privacy_tests`) | `require_user` |
| `POST` | `/api/attack-simulator/run` | Execute 7-vector attack simulation | Judge: `LOCAL_EVALUATOR`; Org: `PLATFORM_ADMIN`, `ORG_ADMIN`, `PRIVACY_OFFICER` |
| `POST` | `/api/passports/{id}/verify` | Live SHA-256 manifest & signature verification | `require_org_access` |
