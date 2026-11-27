# MEDILOCKER M25 — IDENTITY LINKING STRESS REPORT

**Date:** 2026-11-27  
**Suite:** `tests/m25_adversarial_suite/run_m25_eval.py::eval_identity_stress`

## 1. Stress Scenarios Tested (`9` Records, `6` True Patients)

- **P1 (`p1_hosp_a.json`, `p1_hosp_b.json`):** Same patient across hospitals and scripts (`Kavita Deshmukh` ↔ `कविता देशमुख`) with shared phone (`9823456712` / `+91 9823456712`).
- **P2 (`p2_homonym.json`):** Different patient with identical name (`Kavita Deshmukh`), different DOB (`1992-11-03`) and phone (`9811998877`) — homonym trap.
- **P3 (`p3_expanded.json`, `p3_initials.json`):** Same patient with expanded name (`Rajesh Kumar Verma`) vs. initials (`R. K. Verma`) + shared phone & DOB.
- **P4 (`p4_conflict.json`):** Conflicting demographic values (`Rajesh Kumar Verma`, different DOB `1964-09-20` & phone) — transitive-clustering trap.
- **P5 (`p5_hosp_a.json`, `p5_hosp_b.json`):** Cross-hospital `Sunita Devi` (`dob: 1985-06-10`, distinct hospital MRNs `H1-0091` vs `H2-4410`, no shared phone).
- **P6 (`p6_similar_fam.json`):** Similar family name (`Anita Devi`, same DOB `1985-06-10`) — false-merge trap.

## 2. Measured Metrics

- **Units Evaluated:** `9`
- **True-Positive Pairs:** `2`
- **False Merges (`FP`):** **`0`**
- **Missed Links (`FN`):** `1` (`P5` across distinct hospital MRNs without shared phone/national ID)
- **Pairwise Precision:** **`1.0000`**
- **Pairwise Recall:** `0.6667`
- **F0.5:** `0.9091`
- **Cluster Purity:** **`1.0000`**

## 3. Conclusion

The linking engine maintains **zero false merges** and **100% cluster purity** under homonyms, conflicting demographics, initials, and cross-script transliterations, conservatively refusing to merge `P5` across hospitals when only name + DOB match without a shared strong identifier.
