# MEDILOCKER M26 — FILENAME PRIVACY REPORT

**Date:** 2026-11-27

## 1. Root-Cause Audit of the 13 LF-Normalised Filename Leaks

Inspecting the 10 `discharge/` files flagged by `check_dev.py` (`13/3,230` leaks: `10 MRN`, `3 PATIENT_NAME`) showed that **every single one of the 10 files was actually sanitized and renamed** in `sanitized/discharge/`:

| Original Input Path | Category | Actual Output Filename | Root Cause in `check_dev.py` Evaluation |
| :--- | :--- | :--- | :--- |
| `discharge/Discharge_Summary_Shahid_Mohammad_UHID-010607.txt` | `PATIENT_NAME`, `MRN` | `sanitized/discharge/discharge_fn6dfcax49f2.txt` | Original bytes in `dev/truth/truth.json` matched CRLF; blind `.replace(b'\r\n', b'\n')` changed `input_sha256`. |
| `discharge/arogya_ds_ADM000162.txt` | `MRN` | `sanitized/discharge/doc_fn10f0cx3d96.txt` | Same SHA-256 mismatch from blind LF conversion. |
| `discharge/jeevanjyoti_ds_IP-26-00134.txt` | `MRN` | `sanitized/discharge/doc_fn796cex06df.txt` | Same SHA-256 mismatch from blind LF conversion. |
| `discharge/arogya_ds_ADM000170.txt` | `MRN` | `sanitized/discharge/doc_fn898bdxd505.txt` | Same SHA-256 mismatch from blind LF conversion. |
| `discharge/sanjeevani_ds_IPD-2026-00459.txt` | `MRN` | `sanitized/discharge/doc_fn53585x0439.txt` | Same SHA-256 mismatch from blind LF conversion. |
| `discharge/jeevanjyoti_ds_IP-26-00144.txt` | `MRN` | `sanitized/discharge/doc_fn48b73x7e6f.txt` | Same SHA-256 mismatch from blind LF conversion. |
| `discharge/Discharge_Summary_Fatima_Bano_SNJ-26-064508.txt` | `PATIENT_NAME`, `MRN` | `sanitized/discharge/discharge_fn81fb7xb663.txt` | Same SHA-256 mismatch from blind LF conversion. |
| `discharge/Discharge_Summary_Sunil_Mishra_SNJ-26-064511.txt` | `PATIENT_NAME`, `MRN` | `sanitized/discharge/discharge_fnff341x64f4.txt` | Same SHA-256 mismatch from blind LF conversion. |
| `discharge/jeevanjyoti_ds_IP-26-00149.txt` | `MRN` | `sanitized/discharge/doc_fn4f51cx5f60.txt` | Same SHA-256 mismatch from blind LF conversion. |
| `discharge/dhhardoi_ds_DHH-IPD-00591.txt` | `MRN` | `sanitized/discharge/doc_fndf318x8082.txt` | Same SHA-256 mismatch from blind LF conversion. |

## 2. Exact-SHA Development Evaluation & M26 Stress Test

- **Exact-SHA `dev/input` (`check_dev.py`, `3,230` entities across `200` files):**
  - **Personal Data Leaked:** **`0 / 3,230` (`0.0%`)** (`content 0.0%, filename 0.0%, base64 0.0%, metadata 0.0%, key 0.0%, header 0.0%`).
  - **Canaries:** `0 / 4`; **Raw Copies:** `0`; **Medical Data Kept:** `4,847 / 4,855` (`99.8%`).
- **M26 Comprehensive Filename Stress (`test_02_comprehensive_filename_privacy`):**
  - Verified names, short-digit MRNs (`IP-26-00134`, `DHH-IPD-00591`), fullwidth digits, Devanagari + PAN, nested directories, mixed separators (`__`, `--`), multiple extensions (`.tar.txt`), and duplicate filenames across directories — **`0` leaks, `0` path collisions**.
