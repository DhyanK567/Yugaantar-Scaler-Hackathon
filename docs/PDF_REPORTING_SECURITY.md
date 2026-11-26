# MediLocker PDF Reporting — Security Architecture & Controls

**Date:** 2026-11-26  

1. **Strict Allowlist Schemas (`backend/services/pdf_reporting/schemas.py`)**: Only validated aggregate counts, pseudonymous IDs (`PSN-*`, `USR-*`, `DS-*`, `RES-*`), SHA-256 manifest hashes, and safe status/reason codes are accepted. Raw input records, patient names, emails, phones, Aadhaar/ABHA/PAN, OTPs, tokens, and `RAKSHA_SECRET` are never queried or passed to the renderer.
2. **Audit Trail Anonymisation (`service.py`)**: `generate_audit_trail_pdf` queries `actor_id` and `actor_role` (excluding `actor_email`) and renders `_pseudo_actor(actor_role, actor_id)` (`ROLE (USR-<sha256[:8]>)`).
3. **Markup Stripping & XML Escaping (`security.py`)**: `sanitize_safe_text` strips untrusted HTML/ReportLab tags (`<script>`, `<font>`, `<b>`, etc.) and `escape_xml` escapes `&`, `<`, `>` before ReportLab `Paragraph` rendering.
4. **Final Output Security Scan (`scan_pdf_bytes_for_leaks`)**: Every generated PDF byte stream is scanned for `%PDF-` header validity, `RAKSHA_SECRET`, `CANARY_*` tracers, Aadhaar/ABHA/PAN/Phone/Email patterns, and Python tracebacks. Any match raises `PdfSecurityError`, returning HTTP `422` and blocking download.
5. **No Global Monkeypatch**: `backend/services/pdf_reporting/` never imports `generate_pdf.py` and never monkeypatches `hashlib.md5`.
6. **RBAC & Org Isolation (`backend/main.py`)**: All 5 PDF endpoints enforce `require_user` and `require_org_access`, returning `403` on cross-organisation access and `404` on missing records.
