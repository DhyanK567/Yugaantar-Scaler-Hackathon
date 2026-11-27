# MEDILOCKER M25 — M24 INDEPENDENT REPRODUCTION & AUDIT

**Date:** 2026-11-27  
**Evaluator Role:** Independent External Security Evaluator & Healthcare Privacy Benchmark Engineer

## 1. Executive Summary

Independent reproduction of M24 confirms that the submitted engine passes the submission checker (`READY TO SUBMIT`), the 10/10 security regression gate, and the M24 regression test suite (`3/3 passed`). However, independent inspection of exact denominators, ground truth, and `dev/input` outputs uncovered **three important findings**:

1. **M24 Unseen Benchmark Denominator Discrepancy:** M24 reported `20/20` PII probes (`pii_recall: 1.00`), whereas the current `tests/m24_unseen_benchmark/benchmark_m24.py` contains **18** `pii_probes` (`18/18` removed, `0` leaked). Two canary probes were removed when `RX_CANARY` was moved out of `sanitizer.py` so `test_dataset_workflow_e2e.py` could continue verifying canary-leak blocking.
2. **M24 Unseen Benchmark Scope Limit:** `benchmark_m24.py` evaluates 6 files (5 sanitized, 1 quarantined) using case-sensitive substring matching (`if probe in all_san`) on file content only — it does not test NFKC/casefold normalization, filename leakage, or large-scale statistical variance.
3. **35 / 3,230 Development Filename-Only Leaks (`check_dev.py`):**
   - On Windows (CRLF checkout), `dev/input` files differ in `sha256` from `dev/truth/truth.json` (LF hashes) for `175 / 200` files, causing `check_dev.py` to miss `report.json` rename mappings and evaluate original input filenames, producing **35 / 3,230 (`1.1%`)** reported leaks (`24 MRN`, `6 PATIENT_NAME`, `5 PHONE`).
   - Re-running on an **LF-normalized** copy of `dev/input` eliminates the SHA-256 mismatch and reveals **13 / 3,230 (`0.4%`)** remaining filename-only leaks (`10 MRN`, `3 PATIENT_NAME`):
     - `0` content leaks, `0` base64 leaks, `0` metadata/key/header leaks, `0/4` canary leaks, `0` raw copies.
     - The remaining 13 leaks are **real unhandled filename patterns and quarantined-file path references**: e.g., `DHH-IPD-00591`, `IP-26-00134`, `IPD-2026-00459` (where digit groups have `< 6` consecutive digits, bypassing `\d{6,}` in `sanitize_filename()`), plus quarantined files that have `output: null` in `report.json`.

## 2. Exact Reproduced Metrics

| Benchmark / Gate | M24 Reported | M25 Independently Reproduced | Notes |
| :--- | :--- | :--- | :--- |
| `tests/m24_unseen_benchmark/benchmark_m24.py` | `20/20` PII, `17/17` clinical, `P=1.00, R=1.00, F1=1.00` | **`18/18` PII, `17/17` clinical, `P=1.00, R=1.00, F1=1.00`** (`0.899s`, `CONTRACT OK`) | Denominator is `18` probes across `5` sanitized + `1` quarantined file; `Kavita` linked (`PSN-V429ZX`). |
| `tests/m24_unseen_benchmark/test_m24_regressions.py` | `3/3 passed` | **`3/3 passed in 1.73s`** | Verified with `pytest`. |
| `scripts/security_regression_gate.py` | `10/10 passed` | **`10/10 gates passed in 26.76s`** | Verified exit code `0`. |
| `check_submission.py --repo starter --run` | `READY TO SUBMIT` | **`READY TO SUBMIT` (`8.3s`, `CONTRACT OK`)** | Verified offline contract, secret keying, and determinism. |
| `check_dev.py` (Windows `dev/input` CRLF) | `35/3,230` (`1.1%`), `0/4` canary, `4,449/4,457` (`99.8%`), `P=1.00, R=0.76, F0.5=0.94`, `0` false merges | **`35/3,230` (`1.1%`), `0/4` canary, `4,449/4,457` (`99.8%`), `P=1.00, R=0.76, F0.5=0.94`, `0` false merges** | `24 MRN`, `6 PATIENT_NAME`, `5 PHONE`; `175/200` SHA-256 mismatch due to CRLF vs LF. |
| `check_dev.py` (LF-normalized `dev/input`) | Not reported | **`13/3,230` (`0.4%`), `0/4` canary, `4,636/4,644` (`99.8%`), `P=1.00, R=0.75, F0.5=0.94`, `0` false merges** | True filename leak floor before M25 hardening: `10 MRN`, `3 PATIENT_NAME` (`filename 27.1%`). |
| `validate_output.py` on `dev/input` | `CONTRACT OK` | **`CONTRACT OK`** | `200` files: `195` sanitized, `5` quarantined, `823` records. |

## 3. Conclusion

M24's core claims are reproducible, with the caveat that the M24 unseen benchmark is a small (`18`-probe) sanity check and `sanitize_filename()` still leaves short-digit MRN patterns (`< 6` digits per group) exposed in filenames. Phases 2–8 below subject the engine to a 1,000+ record independent synthetic benchmark, adversarial attacks, and targeted hardening.
