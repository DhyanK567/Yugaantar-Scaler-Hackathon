# Milestone — Dynamic PDF Reporting & Evidence Generation Report

**Date:** 2026-11-26  
**Branch:** `feature/guptkavach-privacy-engine`  

---

## 1. Files Created & Modified

### Created
- `backend/services/pdf_reporting/__init__.py`
- `backend/services/pdf_reporting/schemas.py`
- `backend/services/pdf_reporting/security.py`
- `backend/services/pdf_reporting/templates.py`
- `backend/services/pdf_reporting/renderers.py`
- `backend/services/pdf_reporting/service.py`
- `tests/pdf_reporting/test_pdf_reporting.py`
- `docs/PDF_REPORTING_ARCHITECTURE.md`
- `docs/PDF_REPORTING_SECURITY.md`
- `docs/PDF_REPORTING_USER_GUIDE.md`
- `docs/MILESTONE_PDF_REPORTING.md`

### Modified
- `backend/main.py` (5 PDF download/export endpoints with RBAC & security error handling)
- `frontend/src/lib/api.ts` (`downloadPdf` helper + 5 PDF URL builders)
- `frontend/src/app/dashboard/privacy-passports/page.tsx` (**Download PDF**)
- `frontend/src/app/dashboard/privacy-intelligence/page.tsx` (**Export Assessment PDF**)
- `frontend/src/app/dashboard/attack-simulator/page.tsx` (**Download Simulation Report**)
- `frontend/src/app/dashboard/clinical-integrity/page.tsx` (**Export Clinical Report**)
- `frontend/src/app/dashboard/audit/page.tsx` (**Export Audit Report**)

---

## 2. Test & Security Verification Results

```powershell
python -m unittest discover -s tests/pdf_reporting -v
```
- **Result**: **`Ran 5 tests in 0.984s — OK`**
  - `test_01_all_five_operational_pdfs_generate_and_contain_expected_fields`: Verified all 5 PDFs start with `%PDF-`, contain expected report IDs/metrics, and exclude `actor_email` and `RAKSHA_SECRET`.
  - `test_02_missing_report_and_cross_org_access_blocked`: Verified `PdfGenerationError` on missing IDs and org isolation.
  - `test_03_security_scanner_blocks_pii_canary_secret_markup_and_corrupt_pdf`: Verified XML/markup stripping, filename sanitization, and `PdfSecurityError` on Aadhaar, Phone, Email, `CANARY_*`, `RAKSHA_SECRET`, and corrupt PDF bytes.
  - `test_04_large_table_pagination_empty_audit_and_atomic_write`: Verified empty audit PDF, 120-row multi-page pagination (`Page 1 of`, `Page 2 of`), and atomic write leaving zero `.pdf_tmp_*` files.
  - `test_05_no_global_hashlib_monkeypatch_in_backend`: Verified `hashlib.md5(..., usedforsecurity=False)` remains intact.

---

## 3. Environment & Known Limitations

- **Offline Renderer Fallback**: `reportlab` is not installed in the current Python 3.12 environment, so `renderers.py` used the built-in pure-Python stdlib `%PDF-1.4` A4 renderer (`0.984s` for the entire 5-test suite including pipeline execution and 120-row pagination). When `reportlab` is installed, `_render_reportlab_pdf` is used automatically.
- **Submission Brief**: `generate_pdf.py` is preserved unchanged; running it requires `reportlab`.
- **Frontend**: `node_modules` is not installed in this offline environment, so React/TypeScript changes were verified by code inspection.
