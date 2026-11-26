# MediLocker — PDF Reporting & Evidence Generation Architecture

**Date:** 2026-11-26  
**Branch:** `feature/guptkavach-privacy-engine`

---

## 1. Current State

- **`generate_pdf.py`** (repo root): Standalone static script generating the 2-page hackathon submission brief (`starter/GuptKavach_Project_Brief.pdf` and `docs/GuptKavach_Project_Brief.pdf`) with hardcoded benchmark figures. It is **not** imported by `backend/main.py` and must remain preserved as-is for hackathon submission.
- **Authoritative Data Sources (`backend/database.py` / SQLite)**:
  - **Privacy Passports**: `passports` joined with `jobs`, `datasets`, `organisations`, `privacy_assessments`, `clinical_reports`, `identity_clusters`.
  - **Privacy Intelligence**: `privacy_assessments` joined with `jobs`, `datasets`, `organisations`.
  - **Attack Simulation**: `attack_runs` joined with `jobs`, `datasets`, `organisations`.
  - **Clinical Integrity**: `clinical_reports` joined with `jobs`, `organisations`.
  - **Audit Trail**: `audit_events` filtered by authorised `organisation_id` and optional date range (`start_ts`, `end_ts`), excluding any secret/OTP/token fields.

---

## 2. Proposed Subsystem (`backend/services/pdf_reporting/`)

```
backend/services/pdf_reporting/
├── __init__.py
├── schemas.py      # Strict allowlist dataclasses for all 5 operational reports
├── security.py     # XML escaping, markup blocking, PII/canary/secret output scanner
├── templates.py    # A4 MediLocker branding, header/footer, classification, pagination
├── renderers.py    # ReportLab renderer (when installed) + stdlib PDF-1.4 fallback
└── service.py      # Authoritative DB -> Schema -> Render -> Security Scan orchestration
```

### Security & Validation Guarantees
1. **Strict Allowlist Schemas**: Only validated aggregate counts, pseudonymous IDs, hashes, and safe enum/status codes enter PDFs.
2. **No Global Monkeypatches**: Never imports `generate_pdf.py` or monkeypatches `hashlib.md5`.
3. **Final Output Scan**: Every generated PDF byte stream is scanned for prohibited PII patterns (Aadhaar, ABHA, PAN, email, phone), `CANARY_*` tracers, and `RAKSHA_SECRET` before download.
4. **RBAC & Incomplete Job Enforcement**: Backend routes verify `require_user` + `require_org_access`, returning `404` for missing records, `403` for cross-org access, and `409`/`403` for incomplete jobs.
