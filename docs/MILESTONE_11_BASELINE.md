# Milestone 11 — Identity Resolution Baseline

**Date:** 2026-11-26  
**Branch:** `milestone-8/security-audit`  
**Evaluated Output:** `my_output_m8` (`dev/input`, `RAKSHA_SECRET=practice`)

---

## 1. Current Matching Architecture

Identity resolution lives in `starter/raksha_engine/linking.py` (with name normalization in `starter/raksha_engine/names.py` and orchestration in `starter/main.py`):

1. **Evidence Extraction (`RecordClues`):**
   - Extracts `strong_ids` (`abha:<14d>`, `aadhaar:<12d>`, `phone:<10d>`, `email`, `pan`), `mrns` (`mrn:<alnum>`), `name_tokens` (phonetic skeleton list via `normalize_name_tokens()`), `full_phonetic_name`, `gender`, `birth_year`, `age`, `pin`, `district`, and `village`.
   - Note: `mrns` are treated as globally unique without hospital/source scoping (`SNJ/...`, `JJH-...`, `DHH-...`, `UHID-...`).
2. **Blocking Strategy:**
   - Three deterministic blocking dictionaries:
     - `by_strong`: keyed by exact `strong_id`
     - `by_mrn`: keyed by exact normalized `mrn`
     - `by_name`: keyed by exact `full_phonetic_name` (when `>= 2` tokens)
3. **Clustering Method:**
   - Disjoint-set (Union-Find) with cluster-level demographic tracking (`c_gender`, `c_byear`, `c_age`, `c_fname`, `c_global_ids`).
   - `_clusters_compatible()` blocks merges on conflicting gender, birth year (`> 1` yr), age (`> 3` yrs), or first-name phonetic similarity `< 0.72` (unless sharing a global ID).
4. **Pseudonym Generation (`privacy.py`):**
   - `PSN-<6 Crockford base32 chars>` via `HMAC-SHA256(RAKSHA_SECRET, cluster_key)`.
   - `cluster_key` is derived from up to 3 sorted `strong_ids | mrns`, or up to 2 sorted `record_id`s if no IDs exist.

---

## 2. Measured Baseline (`dev/input`)

| Metric | Measured Value |
|---|---:|
| **Contract Validation (`validate_output.py`)** | **`CONTRACT OK`** |
| **Records Processed** | `823` |
| **Records Linked (`patient != null`)** | `776` |
| **Records Unlinked (`patient == null`)** | `47` |
| **Distinct Clusters (`PSN-*`)** | `121` |
| **Pairwise Precision** | **`1.00`** |
| **Pairwise Recall** | **`0.72`** |
| **Pairwise F0.5** | **`0.93`** |
| **False Merges** | **`0`** |
| **Clinical Preservation** | `4455 / 4457` (`100.0%` rounded) |
| **Personal Data Leaked** | `35 / 3230` (`1.1%`, `0.0%` content) |
| **Canaries Leaked** | `0 / 4` |

---

## 3. Known Weaknesses

1. **Unstructured Evidence Objects:** `RecordClues` stores raw sets/strings without per-item metadata (category, confidence, extraction method, conflict status, reason codes).
2. **Name Normalization Gaps:**
   - Initials (`R. Kumar`, `Rahul K.`) and surname-first ordering (`Kumar Rahul`, `Verma, Rajesh K.`) fail exact `full_phonetic_name` blocking (`by_name`).
   - Zero-width characters (`\u200b`) are not stripped before tokenization.
   - `deva_to_latin` + `phonetic_norm` misses some vowel/nasal variations (e.g., `Rahool` vs `Rahul`, `राहुल` vs `Rahul`).
3. **No Hospital/Source Scoping for MRNs:**
   - `mrns` are blocked globally without issuing-hospital context, risking false merges if two hospitals reuse numeric sequences (e.g., `IP-001` at Hospital A vs Hospital B).
4. **No Explicit Abstention / Decision Trail:**
   - Records are simply `PSN-*` or `null` without structured reason codes (`MATCH_STRONG_ID`, `ABSTAIN_CONFLICT_DOB`, `ABSTAIN_WEAK_EVIDENCE`, etc.).
5. **Cluster-Level Conflict Gaps:**
   - `c_mrn` / contradictory `strong_ids` (two different Aadhaar/ABHA numbers in the same cluster) are not checked in `_clusters_compatible()`.
   - Relative-name evidence (`S/o`, `W/o`) and shared family phone risks (parent-child sharing a mobile number) are not explicitly guarded.
6. **File-Order Sensitivity in `cluster_key`:**
   - `by_strong` / `by_mrn` iterate in insertion order (`anchor = idxs[0]`), and if two clusters don't merge due to order-dependent `_clusters_compatible`, cluster membership could depend on traversal order if inputs arrive in different orders.
