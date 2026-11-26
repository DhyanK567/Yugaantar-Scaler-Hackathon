# M16.2 — Identity Linking Report

## 1. Reproduced Metrics (`dev/input` vs `dev/truth/truth.json`)
- **Required Link Units**: `771`
- **True Pairs (`true_pairs`)**: `6,892`
- **True Positives (`tp`)**: `5,551`
- **False Positives (`fp`)**: `0`
- **False Negatives (`fn`)**: `1,341`
- **Precision**: **`1.0000` (`1.00`)**
- **Recall**: **`0.8054` (`0.81`)**
- **F0.5**: **`0.9539` (`0.95`)**
- **False Merges (pseudonyms merging distinct true patients)**: **`0`**

---

## 2. Breakdown of Missed Links (`fn = 1,341`)
1. **Unlinked Units (`2 / 771`)**:
   - `discharge/note_0015.txt` (`PT00010`)
   - `discharge/note_0004.txt` (`PT00002`)
   Both lack sufficient non-ambiguous linking identifiers to merge safely without risking false positives.
2. **Conservative Cluster Splits (`34` true patients)**:
   - Cross-format records (e.g., `notes/nursing_ipd-2026-00454.txt` vs `discharge/sanjeevani_ds_IPD-2026-00454.txt`, or `lab/report_*.json` / `lab/city_results.csv` rows lacking strong shared identifiers) remain in separate conservative clusters rather than merging on weak demographic or partial-name similarity.

---

## 3. Safety Decision
In accordance with M16.2 non-negotiable rules (*"No false merges; ambiguous records must remain separate or unresolved; do not merge patients based on weak name similarity alone"*), the conservative linking thresholds are retained, preserving **Precision = 1.00**, **False Merges = 0**, **Recall = 0.81**, and **F0.5 = 0.95**.
