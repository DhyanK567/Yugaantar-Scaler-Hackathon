# MEDILOCKER M25 — RE-IDENTIFICATION ATTACK EVALUATION

**Date:** 2026-11-27  
**Suite:** `tests/m25_adversarial_suite/run_m25_eval.py::eval_reidentification_attack`

## 1. Threat Model & Attacker Knowledge

- **Attacker Knowledge:** An external adversary holds an auxiliary voter/hospital-intake table of `20` synthetic patients containing quasi-identifiers: exact `age`, `admission date`, `rare diagnosis` (`Wilson's disease`, `Guillain-Barre syndrome`, `Takayasu arteritis`, `Myasthenia gravis`, `Addison's disease`), `city`, and `occupation`.
- **Denominator:** `20` unique target records (`20/20` = `100.0%` uniquely linkable before sanitisation).

## 2. Measured Attack Success Before vs. After Sanitisation

| Metric | Before Sanitisation | After Sanitisation |
| :--- | :--- | :--- |
| **Target Records (Denominator)** | `20` | `20` |
| **Exact QI Tuple Matches (`age` + `admit_date` + `rare_diagnosis`)** | `20 / 20` (`100.0%`) | **`0 / 20` (`0.0%`)** |

## 3. Residual Risk & Limitations

Exact `(age, admit_date, rare_diagnosis)` linkage drops from `100.0%` to `0.0%` because `sanitize_free_text()` generalizes ages into 5-year bands (`age_band()`) and shifts dates deterministically per `(patient_key, RAKSHA_SECRET)` (`shift_dates_in_text()`). However, **zero re-identification risk is not claimed**: rare diagnoses (`Wilson's disease`) and clinical/geographic context remain preserved for medical utility, so an attacker with additional external temporal or rare-disease priors could still narrow candidate sets probabilistically.
