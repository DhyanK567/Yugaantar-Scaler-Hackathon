# MEDILOCKER M25 — CLINICAL PRESERVATION REPORT

**Date:** 2026-11-27  
**Suite:** `tests/m25_adversarial_suite/run_m25_eval.py::eval_clinical_1000`

## 1. Test Scope (`1,000` Clinical Values Across `200` Documents)

Exact string preservation (after NFKC/casefold normalization) was verified across `1,000` clinical assertions covering:
- **Medications & Dosages & Frequencies:** `Metformin 500 mg BD`, `Amlodipine 5 mg OD`, `Atorvastatin 20 mg HS`, `Pantoprazole 40 mg OD`, `Azithromycin 500 mg OD`.
- **Laboratory Values & Units:** `HbA1c 7.4%`, `Creatinine 1.0 mg/dL`, `Hemoglobin 12.8 g/dL`, `WBC 11400 /uL`, `Platelets 185000 /uL`, `TSH 3.8 mIU/L`.
- **Reference Ranges:** `Ref 70-110 mg/dL`, `Ref 3.5-5.1 mEq/L`, `Ref 4000-11000 /uL`.
- **Vitals:** `BP 124/80 mmHg`, `Pulse 76 bpm`, `Temp 38.2 C`, `SpO2 98%`, `RR 18 /min`.
- **Diagnoses, Eponyms & Medical Codes:** `Parkinson's disease`, `Addison's disease`, `Alzheimer's disease`, `Graves' disease`, `Hodgkin's lymphoma`, `Type 2 Diabetes (ICD-10 E11.9)`.

## 2. Results

- **Total Clinical Values Evaluated:** `1,000`
- **Preserved Exactly:** **`1,000` (`100.0%`)**
- **Unexpected Changes:** **`0`**
- **Runtime:** `3.681s`
