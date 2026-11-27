# M16.2 — Clinical Fidelity Report

## 1. Summary
- **Benchmark**: `dev/input` vs `dev/truth/truth.json` via `check_dev.py`
- **Expected Clinical Values**: `4,855`
- **Preserved**: **`4,847` (`99.8%`)**
- **Missing**: **`8`**
- **Modified**: **`0`**
- **Independent Held-Out Evaluation (`tests/independent_eval/run_independent_eval.py`)**: **`36 / 36 (100.0%)`**

---

## 2. Exact Breakdown of All 8 Missing Values
Every single missing value in `check_dev.py` is a `district` quasi-identifier in `registration/arogya_legacy_export.csv`:
- `registration/arogya_legacy_export.csv`, `row:0`, `district`: `Sitapur`
- `registration/arogya_legacy_export.csv`, `row:1`, `district`: `Sitapur`
- `registration/arogya_legacy_export.csv`, `row:2`, `district`: `Sitapur`
- `registration/arogya_legacy_export.csv`, `row:3`, `district`: `Sitapur`
- `registration/arogya_legacy_export.csv`, `row:4`, `district`: `Bahraich`
- `registration/arogya_legacy_export.csv`, `row:5`, `district`: `Sitapur`
- `registration/arogya_legacy_export.csv`, `row:6`, `district`: `Sitapur`
- `registration/arogya_legacy_export.csv`, `row:7`, `district`: `Sitapur`

**0** medications, **0** dosages, **0** lab values, **0** vital signs, and **0** FHIR resources were lost or modified.

---

## 3. Clinical & Privacy Safety Decision
These 8 `district` values were intentionally suppressed (`rare_suppress=True`) by GuptKavach's k-anonymity / rare quasi-identifier protection in `starter/main.py` because `arogya_legacy_export.csv` contains small equivalence classes. Restoring `district` on rare groups would increase singling-out / re-identification risk. Per M16.2 policy (*"Clinical safety and privacy have priority over a cosmetic benchmark score"*), **the safer `4,847 / 4,855 (99.8%)` result is retained**.

---

## 4. Engineering Bug Found & Fixed During Reproduction
During clean-room reproduction with `RAKSHA_SECRET="m16-2-repro-secret-2026"`, `pseudonymous_filename_token()` (introduced in M16.1 as 12 hex digits) could occasionally generate 12 consecutive digits (`0-9`), triggering `PassportSecurityError: Potential raw 12-digit Aadhaar pattern detected in passport artifact!` in `starter/raksha_engine/passport.py`.
- **Fix (`starter/raksha_engine/crypto.py`)**: Formatted `pseudonymous_filename_token()` as `fn<5 hex>x<5 hex>` so `>= 6` consecutive digits can never occur in output filenames.
