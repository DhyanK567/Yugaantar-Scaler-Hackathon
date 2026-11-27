# MEDILOCKER M25 — FINAL INDEPENDENT AUDIT

**Date:** 2026-11-27  
**Track:** Yugaantar DevForge — Track 3: Secret Wards

## 1. Separated Benchmark Results (Never Combined Denominators)

| Benchmark | Denominator / Scope | PII Precision | PII Recall | Clinical Preserved | Identity False Merges | Status |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **M24 Original Unseen (`benchmark_m24.py`)** | `18` probes (`6` files) | `1.0000` | `1.0000` (`18/18`) | `17/17` (`100.0%`) | `0` | Reproduced (note `18` probes, not `20`) |
| **M25 Generated Dev (`dev_gen`, seed `202601`)** | `600` records, `2,375` PII probes | `1.0000` | `1.0000` (`2,375/2,375`) | `2,200/2,200` (`100.0%`) | — | **Passed (`0` leaked)** |
| **M25 Held-Out (`held_out`, seed `202602`)** | `600` records, `2,375` PII probes | `1.0000` | `1.0000` (`2,375/2,375`) | `2,200/2,200` (`100.0%`) | — | **Passed (`0` leaked)** |
| **M25 15-Category Adversarial PII** | `15` categories | `1.0000` all `15` | `1.0000` all `15` | `0` false positives | — | **Passed (`CONTRACT OK`)** |
| **M25 Identity Linking Stress** | `9` records, `6` patients | `1.0000` | `0.6667` (`F0.5=0.9091`) | — | **`0`** (`purity 1.00`) | **Passed (`0` false merges)** |
| **M25 Clinical Preservation Stress** | `1,000` clinical values | — | — | **`1,000/1,000` (`100.0%`)** | — | **Passed (`0` changes)** |
| **M25 Filename & Metadata Privacy** | `8` adversarial paths | — | — | — | — | **`0` path/report/records leaks** |
| **M25 Re-Identification Attack** | `20` QI target records | — | — | — | — | **`20/20` → `0/20` exact QI links** |

## 2. Official Constraints & Verification Gates

- **Offline / CPU-Only / Prohibited Models:** `HF_HUB_OFFLINE=1`, `TRANSFORMERS_OFFLINE=1`; `check_submission.py --repo starter --run` verified `requirements.txt` has no LLM / hosted-AI packages and exited **`0` (`READY TO SUBMIT`, `10.5s`, `CONTRACT OK`)**.
- **Memory & Runtime:** Peak traced Python memory on `600` multi-format records = **`4.69 MB`** (`< 4 GB` limit); runtime = **`4.699s`–`4.994s`** (`< 15 min` limit).
- **Determinism:** Verified by `check_submission.py` (identical `sanitized/` and `records.jsonl` for identical secret; distinct output for different secret; `RAKSHA_SECRET` never written to output/logs).
- **Regression Suites:**
  - `pytest tests/m25_adversarial_suite/test_m25_regressions.py tests/m24_unseen_benchmark/test_m24_regressions.py -v`: **`7 passed in 14.30s`**.
  - `scripts/security_regression_gate.py`: **`GATE STATUS: PASSED (10/10 gates passed) in 30.40s`**.
