# MEDILOCKER M24 — UNSEEN DATASET & ADVERSARIAL BENCHMARK

**Script:** `tests/m24_unseen_benchmark/benchmark_m24.py`  
**Execution Mode:** Offline, CPU-only (`HF_HUB_OFFLINE=1`, `TRANSFORMERS_OFFLINE=1`)

## Corpus Design
- **Held-out CSV (`ward_intake_alpha.csv`):** Reordered unseen columns (`beneficiary_full_name`, `emergency_mobile`, `voter_id_no`, `med_regimen`).
- **Held-out Nested JSON (`lab_follow_up.json`):** Hindi Devanagari (`कविता देशमुख`) matching English CSV row `Kavita Deshmukh` via phone `+91 9823456712`.
- **Held-out FHIR R4 (`discharge_bundle.json`):** `Patient`, `Condition`, and `MedicationRequest` resources.
- **Held-out Hinglish Note (`nursing_note_01.txt`):** `Mareez ka naam`, `Pita ka naam`, `Ghar ka pata`, Voter ID, Driving Licence, Canary, plus clinical eponyms (`Parkinson's disease`, `ASHA worker`, `Dr. Ramesh Kumar`).
- **Adversarial Set (`homonym_and_hindi.txt`, `corrupt_payload.json`):** Devanagari honorifics (`श्रीमती`, `श्री`), Passport (`K4829104`), `Addison's disease`, and malformed JSON (must quarantine).

## Before vs After Comparison (Identical Held-Out + Adversarial Corpus)
| Metric | Baseline Engine | Improved Engine |
|---|---|---|
| Contract (`validate_output.py`) | `CONTRACT OK` | `CONTRACT OK` |
| Files Sanitised / Quarantined | `5` / `1` | `5` / `1` |
| PII Detected & Removed | `11 / 20` (`9` leaked) | `20 / 20` (`0` leaked) |
| PII Precision / Recall / F1 | `1.00` / `0.55` / `0.7097` | `1.00` / `1.00` / `1.00` |
| Clinical Values Preserved | `17 / 17` (`100.0%`) | `17 / 17` (`100.0%`) |
| Cross-Language Linking (`Kavita` ↔ `कविता`) | `True` (`PSN-V429ZX`) | `True` (`PSN-V429ZX`) |
| Runtime | `1.293s` | `0.994s` |
