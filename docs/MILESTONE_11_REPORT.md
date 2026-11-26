# Milestone 11 — Patient Identity Linkage & Cross-Hospital Continuity Report

**Project:** GuptKavach (RAKSHA)  
**Date:** 2026-11-26  
**Branch:** `milestone-8/security-audit`

---

## 1. Baseline Results (`dev/input`, pre-M11)

- **Official Validator:** `CONTRACT OK` (`200` total, `195` sanitized, `5` quarantined, `823` records)
- **Records Linked / Unlinked:** `776` linked / `47` unlinked (`121` clusters)
- **Practice Self-Check (`check_dev.py`):** `Precision = 1.00`, `Recall = 0.72`, `F0.5 = 0.93`, `False Merges = 0`
- **M11.8 Adversarial Identity Suite (pre-fix):** `TP = 7`, `FP = 4`, `FN = 3`, `Precision = 0.636`, `Recall = 0.700`, `F0.5 = 0.648`, `False Merges = 4`, `Abstentions = 3`

---

## 2. Existing Weaknesses Addressed

1. **Cluster-Key Collisions on Shared Family Phones (`FP = 1`):** Two separate clusters that did not merge during clustering (e.g., parent and child sharing a phone number) could emit the same `cluster|<phone>` key and collide onto the same `PSN-*` pseudonym.
2. **Contradictory Strong-ID Blind Spot (`FP = 2`):** `by_name` linking did not block merges when two records carried conflicting Aadhaar/ABHA/PAN numbers, and `_clusters_compatible()` did not track all cluster strong IDs.
3. **Global MRN Assumption (`FP = 1`):** Unprefixed MRNs (`IP001`) were treated as globally unique across hospitals.
4. **Initials & Surname-First Blind Spot (`FN = 3`):** `Rajesh Kumar Verma`, `Verma, Rajesh K.`, and `R. K. Verma` failed to link (`0.00` recall in `name_supporting`).
5. **Zero-Width Character Evasion:** `\u200b`–`\u200d` and `\ufeff` were not stripped before name tokenization.

---

## 3. New Identity Architecture

- **`EvidenceItem` (`starter/raksha_engine/linking.py`):** Structured evidence records (`category`, `normalized`, `source_record`, `strength`, `method`, `conflict`, `reason_code`) plus per-record `decision_reason` (`MATCH_STRONG_ID`, `MATCH_MRN`, `MATCH_CORROBORATED_NAME`, `MATCH_INITIAL_CORROBORATED`, `ABSTAIN_CLUSTER_CONFLICT`, `ABSTAIN_WEAK_EVIDENCE`, `SINGLETON_STRONG_ID`).
- **Order-Independent Execution:** `resolve_identities()` sorts all `RecordClues` deterministically by `record_id` prior to blocking and clustering.

---

## 4. Evidence Categories & Matching Policy

| Tier | Evidence | Policy |
|---|---|---|
| **A. Strong** | `ABHA`, `AADHAAR`, `PAN`, `EMAIL`, `PHONE`, hospital-scoped `MRN` | Links if `_compatible()` & `_clusters_compatible()` pass; `PHONE` never overrides conflicting gender/DOB/name. |
| **B. Supporting** | Phonetic full name, surname + initials, `birth_year`, `age`, `pin`, `district`, `village` | Name alone never merges; full name requires `score >= 3` with `birth_year` or `pin`; initials require exact `birth_year` + geo match. |
| **C. Conflict** | Different `AADHAAR`/`ABHA`/`PAN`, `gender` mismatch, `birth_year` diff `> 1`, `age` diff `> 3` | Blocks merge at both pairwise and cluster levels (`ABSTAIN_CLUSTER_CONFLICT`). |

---

## 5. Multilingual Normalisation (`starter/raksha_engine/names.py`)

- NFKC normalization + zero-width character stripping (`\u200b-\u200d\ufeff`).
- Devanagari-to-Latin phonetic transliteration (`deva_to_latin`) + phonetic skeleton (`phonetic_norm`).
- Comma-separated `"Surname, Given M."` reordering (`Verma, Rajesh K.` → `rajesh k verma`).
- Initial-aware comparison (`names_match_with_initials`) supporting `R. K. Verma` ↔ `Rajesh Kumar Verma` when corroborated.

---

## 6. Cross-Hospital Resolution & Cluster Conflict Prevention

- **Hospital-Scoped MRNs (`_scoped_mrn`):** Unprefixed MRNs are scoped as `mrn:<hospital>:<id>`, preventing `HospitalA:IP001` from colliding with `HospitalB:IP001`.
- **Cluster-Level Conflict Guard (`_clusters_compatible`):** Tracks `c_all_strong`, `c_gender`, `c_byear` range, `c_age` range, and `c_itoks` across the entire cluster to block transitive false-merge chains (`A`–`B`–`C`).

---

## 7. Pseudonym Generation (`privacy.py` & `linking.py`)

- Domain-separated HMAC-SHA256 (`PSN-<6 Crockford base32>`), keyed by `RAKSHA_SECRET`.
- **Shared-ID Disambiguation (`sid_to_clusters`):** If a `strong_id` or `mrn` appears in more than one distinct cluster (e.g., family phone), `cluster_key` is disambiguated with the cluster's deterministic anchor `record_id` (`cluster|<anchor_rid>|<sids>`), guaranteeing separate clusters never receive the same `PSN-*`.

---

## 8. Adversarial Identity Benchmark Results (`tests/identity_adversarial/run_identity_benchmark.py`)

| Category | TP | FP | FN | Precision | Recall | F0.5 | False Merges | Abstentions |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| **Strong ID** | 1 | 0 | 0 | `1.000` | `1.000` | `1.000` | `0` | 0 |
| **Cross-Hospital** | 1 | 0 | 0 | `1.000` | `1.000` | `1.000` | `0` | 0 |
| **Multilingual** | 2 | 0 | 0 | `1.000` | `1.000` | `1.000` | `0` | 0 |
| **Name Supporting (Initials / Surname-First)** | 3 | 0 | 0 | `1.000` | `1.000` | `1.000` | `0` | 0 |
| **False-Merge Adversarial** | 1 | 0 | 0 | `1.000` | `1.000` | `1.000` | `0` | 0 |
| **Uncertain** | 0 | 0 | 0 | `1.000` | `1.000` | `1.000` | `0` | 2 |
| **OVERALL (29 records)** | **10** | **0** | **0** | **`1.000`** | **`1.000`** | **`1.000`** | **`0`** | **2** |

- **Shuffled-Order Invariance:** `True` (identical pseudonyms across shuffled input order).
- **Cross-Secret Collisions:** `0`.

---

## 9. Practice Dataset & Submission Verification (`dev/input`)

| Check | Result |
|---|---|
| `validate_output.py --input dev/input --output my_output_m11` | **`CONTRACT OK`** |
| `check_dev.py --output my_output_m11` (Linking) | **`Precision = 1.00`**, `Recall = 0.72`, **`F0.5 = 0.93`**, **`False Merges = 0`** |
| `check_dev.py` (Personal Data / Canaries / Clinical) | `35/3230` (`1.1%`, `0.0%` content), `0/4` canaries, `4455/4457` (`100.0%`) clinical |
| `records.jsonl` Counts | `823` total, `776` linked, `47` unlinked, `153` distinct clusters |
| Determinism (2 runs, `RAKSHA_SECRET=practice`) | `sanitized_identical = True` (`195` files), `records_identical = True` (`823` records) |
| Cross-Secret Unlinkability (`practice` vs `other_secret`) | `0` pseudonym collisions across `776` linked records |
| `check_submission.py --repo starter` | **`READY TO SUBMIT`** |
| Performance (`dev/input`) | **`5.29s`** wall-clock time; `9.49 ms` / `36.0 KB` on M11.8 suite |

---

## 10. Remaining Limitations

- Practice recall on `dev/input` remains `0.72` (`153` clusters for `48` true patients) because records lacking both strong IDs and structured `birth_year`+geo corroboration conservatively abstain rather than risking false merges.
- `tests/adversarial/run_adversarial.py` still flags the Phase 2 `CANARY_*` literal token test (`3/4`) and `filename` channel reporting (`35/3230` in `check_dev.py`), which are separate from Milestone 11 identity resolution.
