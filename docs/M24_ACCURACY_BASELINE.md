# MEDILOCKER M24 — ACCURACY BASELINE REPORT

**Date:** 2026-11-27  
**Engine Version:** `guptkavach-engine/15.5` (`starter/main.py` + `starter/raksha_engine/*`)

---

## 1. Reconciled Existing Benchmark Results (Baseline)

All historical denominators are reconciled here using direct execution on the current codebase:

| Benchmark | Split / Scope | PII Detection | Clinical Preservation | Identity Resolution | Privacy & Reliability |
|---|---|---|---|---|---|
| **Official Practice Self-Check (`check_dev.py`)** | `dev/input` (`200` files, `823` records) | `35 / 3,230` (`1.1%`) leaked — 100% in `filename` (`0.0%` content, `0.0%` deva, `0.0%` hinglish) | `4,449 / 4,457` (`99.8%`) | `P=1.00, R=0.76, F0.5=0.94` (`0` false merges) | `0 / 4` canary leaks; `0` raw copies; `CONTRACT OK` |
| **Multilingual Evaluator (`test_multilingual_pii.py`)** | `18` synthetic cases (EN/HI/Hinglish) | `TP=22, FP=0, FN=0` (`P=1.000, R=1.000, F1=1.000`) | `30 / 30` (`100.0%`) safe clinical preserved | N/A (text-level suite) | `14.91 ms` (`0.83 ms/case`) |
| **Independent Held-Out Eval (`run_independent_eval.py`)** | `5` files (`4` sanitized, `1` quarantined), `8` records | `0 / 10` direct PII leaked | `36 / 36` (`100.0%`, `0` missing, `0` modified) | `8 / 8` linked | `0 / 2` canaries leaked; `6 -> 0` unique records; `0.991s`, `29.68 MB` RSS |

---

## 2. Baseline Architecture Strengths & Target Gaps for Unseen Data

1. **Strengths:** Conservative cross-hospital identity linking (`0` false merges), strong Devanagari/Hinglish transliteration matching, clinical eponym/dosage guards, deterministic HKDF/HMAC pseudonymisation, and strict offline CPU-only execution.
2. **Unseen-Dataset Gaps to Evaluate & Harden:**
   - Unfamiliar CSV/JSON field aliases (e.g., `next_of_kin_contact`, `emergency_phone`, `epic_id`, `voter_id`, `driving_licence`, `passport_no`, `beneficiary_full_name`, `nominee_name`).
   - Indian secondary identity patterns in free text (Voter ID `ABC1234567`, Driving Licence `MH12 20180012345`, Passport `[A-Z]\d{7}` with contextual label).
   - Mixed-script & Unicode NFKC edge cases (e.g., fullwidth digits, zero-width joiners, honorific variations like `Shri`, `Smt.`, `श्री`, `श्रीमती`, `Mareez ka naam`, `Ghar ka pata`).
   - Context disambiguation between patient names vs doctor/hospital/eponym collisions in unseen notes.
