# M16.1 — Filename Privacy Fix & Verification Report

## 1. Summary of Fix
Hardened GuptKavach output filename handling to eliminate PII leakage while using domain-separated, secret-keyed pseudonymisation:

- **Domain-separated key derivation (`starter/raksha_engine/crypto.py`)**:
  - Added `HKDF_DOMAIN_FILENAME = b"medilocker:v1:filename-pseudonym"`.
  - Added `pseudonymous_filename_token(rel_posix, raw_sha256, secret, length=12)` using HKDF-SHA256 + HMAC-SHA256, ensuring deterministic output for identical `(input, RAKSHA_SECRET)`, secret separation across different `RAKSHA_SECRET` values, and collision resistance across duplicate-content files.
- **Hardened filename sanitisation (`starter/raksha_engine/sanitizer.py`)**:
  - Updated `sanitize_filename(rel_posix, name_index, raw_sha256, secret=b"")` to:
    - Strip path traversal (`..`), null bytes, backslashes, and drive prefixes.
    - Check underscore-, hyphen-, dot-, and space-separated variants with `local_first_names=name_index.first_names`.
    - Flag non-ASCII/Devanagari characters, unsafe punctuation, and `>= 6`-digit identifiers in filenames.
    - Restrict retained filename prefixes on renamed files to a strict clinical allowlist (`_SAFE_FILENAME_PREFIXES`), defaulting to `doc`.
- **Engine integration (`starter/main.py`)**:
  - Passed `SECRET` to `sanitize_filename(rel, name_index, sha, secret=SECRET)` and used `pseudonymous_filename_token(f"collision:{rel}", sha, SECRET, length=8)` on path collisions.
  - Quarantined files continue to emit `output: null` in `report.json` with zero raw filename exposure.

---

## 2. Before / After Comparison
| Metric | Audit Baseline | M16.1 Verified Result |
|---|---:|---:|
| Direct PII leaked (overall) | 35 / 3,230 | **0 / 3,230 (0.0%)** |
| Filename channel leakage | 35 (24 MRNs, 6 names, 5 phones) | **0.0%** |
| Content channel leakage | 0% | **0.0%** |
| Canary leaks | — | **0 / 4** |
| Medical data preserved | — | **4,847 / 4,855 (99.8%)** |
| Patient linking | — | **Precision 1.00, Recall 0.81, F0.5 0.95 (0 false merges)** |
| Raw copies exported | — | **0** |
| Output contract | — | **CONTRACT OK** |
| Submission checker | — | **READY TO SUBMIT** |

---

## 3. Files Changed
- `starter/raksha_engine/crypto.py`
- `starter/raksha_engine/sanitizer.py`
- `starter/main.py`
- `tests/cryptography/test_filename_privacy.py`
- `scripts/verify_submission.ps1`
- `scripts/verify_submission.sh`
- `docs/M16_1_FILENAME_LEAKAGE_ROOT_CAUSE.md`
- `docs/M16_1_FILENAME_PRIVACY_FIX_REPORT.md`
