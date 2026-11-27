# MEDILOCKER M26 — IDENTITY CONTINUITY REPORT

**Date:** 2026-11-27  
**Evaluator Role:** Independent Healthcare Identity-Resolution Engineer

## 1. Root Cause of Missed Identity Links in M25

In the M25 identity stress test (`eval_identity_stress()`), `P5` (`Sunita Devi`, `dob: 1985-06-10` across `H1-0091` and `H2-4410`) was missed (`recall = 0.6667`, `F0.5 = 0.9091`) because `RecordClues` (`starter/raksha_engine/linking.py`) and `starter/main.py` extracted only `birth_year` (`1985`) from `DOB` fields and discarded the month and day. Without `pin`, `district`, `village`, or `age`, `birth_year` alone scored `2 < 3` and abstained.

## 2. Conservative Multi-Signal Enhancement

Added `exact_dob` (`YYYY-MM-DD`) via `parse_exact_dob()` in `starter/raksha_engine/linking.py` and wired it into JSON/FHIR and CSV clue extraction in `starter/main.py`:
- **Conflict Guard:** `_compatible()` rejects pairs with differing `exact_dob` values.
- **Exact Name + Exact DOB (`YYYY-MM-DD`):** Contributes `score += 3` in `resolve_identities()` (1-in-21,900+ date collision odds), linking records across hospitals when full phonetic names match without conflicting IDs/gender.
- **Initials + Expanded Name + Exact DOB:** Allows `names_match_with_initials()` matches (e.g., `S. K. Iyer` ↔ `Suresh Kumar Iyer`) when `exact_dob` matches cleanly.
- **Name/Hospital/Diagnosis Only:** Still strictly blocked (`0` false merges).

## 3. Measured Identity Continuity Results

| Benchmark | Pre-M26 | Post-M26 |
| :--- | :--- | :--- |
| **M25 Identity Stress (`9` records, `6` patients)** | `P=1.00, R=0.6667, F0.5=0.9091, FP=0, purity=1.00` | **`P=1.00, R=1.00, F0.5=1.00, FP=0, FN=0, purity=1.00`** |
| **M26 Held-Out Identity (`7` records, `5` patients)** | — | **`TP=2, FP=0, FN=0` (`test_01_held_out_identity_continuity_zero_false_merges`)** |
| **Development Benchmark (`dev/input`, `check_dev.py`)** | `P=1.00, R=0.75–0.76, F0.5=0.94, FP=0` | **`P=1.00, R=0.81, F0.5=0.95, FP=0`** |
