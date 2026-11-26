# Milestone 14 — Performance Engineering Baseline

**Date:** 2026-11-26  
**Environment:** Windows 11, Python 3.14.7, CPU-only, `.venv`  
**Target Evaluation Constraints:** 2 CPUs, 4 GB RAM, 15 minutes (`900s`), offline execution.

---

## 1. Baseline Measurements (`dev/input`)

| Metric | Measured Baseline |
|---|---|
| **Total Input Files** | `200` (`645,582` bytes) |
| **Sanitized / Quarantined Files** | `195` / `5` |
| **Records Processed** | `823` |
| **Total Sanitized Output Bytes** | `5,136,406` bytes |
| **Unprofiled Wall-Clock Time** | `10.15s` (run 1), `9.49s` (run 2) — mean **`9.82s`** |
| **Throughput (mean)** | **`20.37` files/sec**, **`83.81` records/sec** |
| **Profiled Runtime (`cProfile` + `tracemalloc`)** | `62.64s` (`4,142,026` function calls) |
| **Peak Python Traced Memory** | **`19.78 MB`** |

---

## 2. `cProfile` Top Bottlenecks (`dev/input`)

| Hotspot | Calls | CumTime (Profiled) | Root Cause |
|---|---:|---:|---|
| `sanitize_free_text` | `20,575` | `34.135s` (55.4%) | Runs base64 regex (`>=24` chars), 10 digit/ID regexes, and date-shift regexes on every short string & JSON key without fast-path pre-checks. |
| `redact_names_in_text` | `20,575` | `17.159s` (27.9%) | Runs doctor/relative/labeled/honorific/corpus regexes on numeric/punctuation-only strings and short tokens. |
| `re._compile` | `183,070` | `3.284s` | Uncompiled `re.sub` / `re.search` calls inside hot loops (`sanitize_free_text`, `shift_dates_in_text`, `extract_clues_from_text`, `normalize_name_tokens`). |
| `classify_field` | `15,388` | `2.195s` | Re-normalizes and runs 23 `_COL_RULES` regexes on the same repeated JSON keys (`visits`, `rx`, `diagnosis`, `code`, `display`). |
| `resolve_identities` + `_compatible` | `1` / `17,077` | `3.801s` + `2.827s` | Pairwise checks and repeated `SequenceMatcher` calls on blocking buckets. |

---

## 3. Optimisation Plan (M14.2–M14.7)

1. **M14.2 (Memory-Efficient Ingestion):** Bound JSON/CSV buffering and avoid holding raw file bytes or redundant strings across Pass 1 → Pass 2 (free `raw` immediately; stream CSV rows).
2. **M14.3 (PII & Regex Optimisation):**
   - Pre-compile all module-level regexes (eliminating ~180,000 `re._compile` calls).
   - Add bounded `functools.lru_cache(maxsize=4096)` on pure metadata/schema functions (`classify_field`, `is_clinical_safe_field`) — zero patient data cached.
   - Add fast-path character/length guards in `sanitize_free_text` (skip `_B64_RX` if `len < 24`; skip digit regexes & date shifting if no ASCII/Devanagari digit; skip `@` regexes if `"@" not in work`; skip `redact_names_in_text` if `< 3` chars or no alpha).
3. **M14.4 (Scalable Identity Blocking):** Skip `SequenceMatcher` when first characters/lengths are incompatible or tokens already match; keep blocking deterministic and order-independent.
4. **M14.6 (Parallelism Decision):** Evaluate whether sequential vs bounded `ProcessPoolExecutor(max_workers=2)` is faster on 2 CPUs (given Python subprocess spawn overhead on Windows and global `CorpusNameIndex` + `resolve_identities` synchronization).
5. **M14.7 (Fault Tolerance & Atomic Output):** Write `sanitized/`, `records.jsonl`, and `report.json` via a staging directory / atomic rename or clean rollback so partial/incomplete runs never leave a deceptive `report.json` or raw data in `sanitized/`.
