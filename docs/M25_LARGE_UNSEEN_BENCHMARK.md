# MEDILOCKER M25 — LARGE INDEPENDENT SYNTHETIC BENCHMARK

**Date:** 2026-11-27  
**Generator:** `tests/m25_adversarial_suite/m25_generator.py`  
**Evaluator:** `tests/m25_adversarial_suite/run_m25_eval.py`

## 1. Benchmark Design (1,200 Synthetic Records, Separate Splits)

Two independent 600-record synthetic splits (`1,200` total records) were generated with distinct random seeds, never sharing denominators:
- **M25 Generated Development Split (`dev_gen`, seed `202601`):** `600` records across `134` files (`129` sanitized, `5` empty/malformed or multi-format bundles).
- **M25 Held-Out Split (`held_out`, seed `202602`):** `600` records across `134` files.

Both splits cover:
- Reordered CSVs with unseen column aliases (`beneficiary_full_name`, `emergency_mobile`, `voter_id_no`, `mrn_code`, `guardian_person`, `clinical_diagnosis`, `med_regimen`).
- Nested JSON with mixed English, Devanagari, and Romanised Hindi keys (`naam`, `contact_num`, `aadhaar_id`, `pata`).
- JSONL referral streams (`patient_full_name`, `abha_no`, `pan_card`).
- FHIR R4 Bundles (`Patient`, `Condition`, `MedicationRequest`).
- Unstructured discharge summaries, Hinglish nursing notes, Devanagari clinical notes, and initial-based referral notes.

## 2. Pre-Hardening vs. Post-Hardening Results (Separate Denominators)

| Split | Phase | PII Total | PII Removed | PII Leaked | Precision | Recall | F1 | Clinical Preserved | Runtime |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **`dev_gen` (seed `202601`)** | Pre-Hardening | `2,375` | `2,367` | `8` (`RELATIVE_NAME`) | `1.0000` | `0.9966` | `0.9983` | `2,200 / 2,200` (`100.0%`) | `7.219s` |
| **`dev_gen` (seed `202601`)** | **Post-Hardening** | **`2,375`** | **`2,375`** | **`0`** | **`1.0000`** | **`1.0000`** | **`1.0000`** | **`2,200 / 2,200` (`100.0%`)** | **`4.699s`** |
| **`held_out` (seed `202602`)** | Pre-Hardening | `2,375` | `2,363` | `12` (`3 PATIENT_NAME`, `9 RELATIVE_NAME`) | `1.0000` | `0.9949` | `0.9975` | `2,200 / 2,200` (`100.0%`) | `7.059s` |
| **`held_out` (seed `202602`)** | **Post-Hardening** | **`2,375`** | **`2,375`** | **`0`** | **`1.0000`** | **`1.0000`** | **`1.0000`** | **`2,200 / 2,200` (`100.0%`)** | **`4.994s`** |

## 3. Root Causes Fixed Between Pre- and Post-Hardening

- Uppercase `S/O` (e.g. `S/O Sunita Nair`) in discharge summaries was missed because `RX_RELATIVE` only matched `S/o` and `s/o`. Fixed in `starter/raksha_engine/names.py`.
- All `3` `PATIENT_NAME` leaks in `held_out` were caused by those same names appearing as `RELATIVE_NAME` in `notes/` under `S/O`. Fixing `RX_RELATIVE` eliminated both `PATIENT_NAME` and `RELATIVE_NAME` leaks without any dataset-specific rules.
