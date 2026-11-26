# MEDILOCKER — HEALTHCARE DATA PRIVACY & INTEGRITY REPORT

**Document Specification & Metric Provenance**

---

## 1. Architecture & Workflow Integration

The **MediLocker Healthcare Data Privacy & Integrity Report** is a 3-page A4 monochrome PDF generated dynamically by the FastAPI backend (`backend/privacy_report_pdf.py`) from live SQLite assessment tables and on-disk job outputs (`GET /api/jobs/{job_id}/privacy-report.pdf`).

### Security & Access Controls
- **Authentication & Organisation Isolation**: Enforces `require_user` and `require_org_access(user, job["organisation_id"])`. Unauthenticated requests return `401`; cross-organisation requests return `403`.
- **Zero Side Effects**: Uses ReportLab (`reportlab.platypus.BaseDocTemplate`) without global cryptographic monkeypatching or modifying `starter/`.
- **Safe Dynamic Rendering**: All dynamic strings are scrubbed for accidental PII patterns (Aadhaar, phone, email), local paths, and `RAKSHA_SECRET`, XML-escaped before `Paragraph` rendering, and Devanagari (`\u0900-\u097F`) runs are wrapped in a registered Unicode font (`Nirmala.ttc` on Windows).
- **Dashboard Integration**: Available directly from `frontend/src/app/dashboard/datasets/page.tsx` via the **"Generate Privacy & Integrity Report"** button on both the active job banner and registered dataset rows.

---

## 2. Page-by-Page Metric Provenance

| Page | Section | Source Table / Artifact | Missing-Data Behavior |
|---|---|---|---|
| **Page 1** | Top Metadata Panel | `jobs` (`id`, `completed_at`, `release_decision`) | `REVIEW REQUIRED` if incomplete |
| **Page 1** | `01 DATASET INFORMATION` | `datasets`, `organisations`, `jobs`, `report.json` | `Not available` / `Not measured` |
| **Page 1** | `02 PRIVACY DETECTION & PROTECTION` | `privacy_assessments` | `Not measured` / `Not run` |
| **Page 1** | `03 IDENTITY CONTINUITY` | `identity_clusters` | `Not measured` (never substituted with `0`) |
| **Page 2** | `04 CLINICAL INTEGRITY` | `clinical_reports` + `details_json.categories` | `Not measured` per category |
| **Page 2** | `05 RE-IDENTIFICATION RISK ASSESSMENT` | `privacy_assessments.details_json.risk_map` | `Distribution not measured` |
| **Page 2** | `06 ADVERSARIAL ATTACK SIMULATION` | `attack_runs` + `privacy_assessments` | `Not run` / `Not measured` |
| **Page 3** | `07 PRIVACY PASSPORT` | `passports` + live `verify_passport_bundle()` | Distinguishes `UNSIGNED` vs `TAMPERING DETECTED` vs `VERIFIED` |
| **Page 3** | `08 PROCESSING & SECURITY SUMMARY` | `jobs` (`files_quarantined`, `files_sanitized`, `duration_secs`) | `Not measured` for unmeasured peak RSS |
| **Page 3** | `09 FINAL RELEASE DECISION` | Derived from `jobs.release_decision` & `status` | `PASS` / `BLOCKED` / `REVIEW REQUIRED` |
| **Page 3** | `10 AUTHORISED REVIEW & GOVERNANCE` | `privacy_passport.json` (`engine_version`, `policy_version`) | `Not assigned` when reviewer omitted |

---

## 3. Sample Output & Verification

- Sample PDF generated from a live synthetic evaluation run: `submission/MediLocker_Privacy_Integrity_Report_Sample.pdf` (3 pages, A4 portrait).
- Automated test suite: `tests/privacy_report/test_privacy_report_pdf.py` (`python -m pytest tests/privacy_report/test_privacy_report_pdf.py -v`).
