# Milestone 14 — Performance Engineering, Scalability & Reliability Report

**Project:** GuptKavach (RAKSHA)  
**Date:** 2026-11-26  
**Target Evaluation Budget:** 2 CPUs, 4 GB RAM, 15 minutes (`900s`), offline CPU-only execution.

---

## 1. Baseline Environment & Profiling Methodology

- **Environment:** Windows 11, Python 3.14.7, `.venv` (standard library only, CPU-only).
- **Methodology:** Profiled `starter/main.py` on `dev/input` (`200` files, `823` records, `645,582` input bytes) using `cProfile` + `tracemalloc`, plus two unprofiled wall-clock runs.

---

## 2. Bottlenecks Identified

1. **Repeated Regex Compilation (`re._compile`):** `183,070` calls (`3.284s` profiled) from uncompiled `re.sub`/`re.search` in `privacy.py`, `patterns.py`, `sanitizer.py`.
2. **Unfiltered `sanitize_free_text` (`20,575` calls, `55.4%` of profiled time):** Ran base64 regex (`>= 24` chars), 10 digit/ID regexes, email/ABHA `@` regexes, and date-shift regexes on every short string and JSON key (`"visits"`, `"code"`, `"650 mg"`).
3. **Unfiltered `redact_names_in_text` (`20,575` calls, `27.9%` of profiled time):** Ran doctor/relative/honorific/corpus regexes on numeric/punctuation-only strings.
4. **Repeated Schema Classification (`classify_field`, `15,388` calls):** Re-ran 23 regexes on the same repeated JSON keys (`visits`, `rx`, `diagnosis`, `display`).

---

## 3. Optimisations Implemented

1. **Pre-compiled Module-Level Regexes (`patterns.py`, `privacy.py`, `sanitizer.py`):** Eliminated hot-loop `re._compile` calls across date parsing, text date shifting, age-band matching, and field-classification overrides.
2. **Bounded Schema Cache (`patterns.py`):** Added `@functools.lru_cache(maxsize=4096)` on `classify_field(name)` and `is_clinical_safe_field(name)` (pure column/key schema strings only; **zero** patient data cached).
3. **Fast-Path Character & Length Guards (`sanitizer.py`, `names.py`, `privacy.py`):**
   - `sanitize_free_text`: skip `sanitize_base64_in_text` when `len < 24`; skip all digit/ID/PIN/DOB/age/date-shift regexes when `not any(c.isdigit() for c in work)`; skip email/ABHA-address regexes when `"@" not in work`.
   - `redact_names_in_text`: return `(text, 0)` immediately when `len < 3` or no alphabetic character; skip `RX_DOCTOR` when `"dr"` / `"डॉ"` is absent.
4. **Identity Candidate Blocking (`linking.py`):** Deterministic `record_id`-sorted blocking (`by_strong`, `by_mrn`, `by_name`, `by_surname`) avoids $O(N^2)$ all-pairs comparison ($823 \times 822 / 2 = 338,253$ possible pairs reduced to sparse intra-block pairs).
5. **Cryptographic & Parallelism Decisions:**
   - **Crypto:** `pseudonym()` and `date_shift_days()` use fast keyed `HMAC-SHA256` (~microseconds per record) with zero disk staging or insecure caching.
   - **Parallelism:** Retained deterministic sequential execution rather than `ProcessPoolExecutor` because `CorpusNameIndex` and `resolve_identities()` require global cross-file state, Windows/2-CPU process-spawn overhead (~1.5–2s/worker) exceeds savings on 200-file batches, and sequential execution guarantees 100% determinism and `< 20 MB` peak Python memory.
6. **Fault Tolerance & Atomic Output (`starter/main.py`):** `report.json` is written atomically via `.report.json.tmp` + `os.replace()`, preventing partial/corrupt reports on interruption; malformed/unsupported files are strictly quarantined.

---

## 4. Before / After Measurements (`dev/input`, 200 files, 823 records)

| Metric | Baseline (M14.1) | Optimised (M14) | Change |
|---|---:|---:|---|
| **Wall-Clock Time (2 runs)** | `10.15s` / `9.49s` (mean `9.82s`) | `7.35s` / `6.99s` (mean **`7.17s`**) | **`-27.0%` faster** |
| **Throughput (Files / sec)** | `20.37` | **`26.6`–`28.6`** | **`+30%`–`+40%`** |
| **Throughput (Records / sec)** | `83.81` | **`109.3`–`117.7`** | **`+30%`–`+40%`** |
| **Peak Python Traced Memory** | `19.78 MB` | `< 20 MB` (limit `4,096 MB`) | Well within budget |

---

## 5. Load & Stress Benchmarks (`tests/performance/benchmark_suite.py`)

| Workload Tier | Files (Sanitized / Quarantined) | Records | Wall Time | Files/sec | Records/sec |
|---|---:|---:|---:|---:|---:|
| **Small (`dev/input`)** | `200` (`195` / `5`) | `823` | **`7.53s`** | `26.6` | `109.3` |
| **Medium (Synthetic)** | `1,000` (`975` / `25`) | `1,225` | **`24.88s`** | `40.2` | `49.2` |
| **Large (Synthetic)** | `5,000` (`4,875` / `125`) | `6,125` | **`103.61s`** | `48.3` | `59.1` |

- **5,000-file Large Workload:** Completed in **`103.61s`** (~1.7 minutes — **8.7× faster** than the 15-minute / `900s` limit), with linear/sub-linear scaling (`48.3` files/s vs `26.6` files/s on Small).

---

## 6. Failure-Recovery & Cross-Milestone Regression Results

- **Fault Tolerance (`benchmark_suite.py`):**
  - Corrupt JSON, empty CSV, and raw PDF quarantined (`quarantined: 3`, `sanitized: 1`), `raw_leaked_into_sanitized: false`.
  - Clean rerun over same output directory: `exit_codes: [0, 0]`, `records_after_rerun: 1` (zero duplicates).
- **Contract Validator (`validate_output.py`):** **`CONTRACT OK`**
- **Practice Self-Check (`check_dev.py`):** `1.1%` leaked (`content 0.0%`, `deva 0.0%`, `hinglish 0.0%`), `0/4` canaries, `4449/4457` (`99.8%`) clinical preserved, `Precision = 1.00`, `Recall = 0.76`, `F0.5 = 0.94`, `False Merges = 0`.
- **Adversarial Identity Suite (`run_identity_benchmark.py`):** `Precision = 1.000`, `Recall = 1.000`, `F0.5 = 1.000`, `False Merges = 0`, `Order invariance = True`.
- **Determinism:** `sanitized_identical = True` (`195` files), `records_identical = True` (`823` records).
- **Submission Checker (`check_submission.py --repo starter`):** **`READY TO SUBMIT`**

---

## 7. Remaining Bottlenecks

- On Windows, `resource.getrusage` is unavailable so `report.json` records `peak_rss_mb: 0.0` (populated automatically on the Linux evaluation sandbox).
- `5,000` files run in `103.61s`; a `10,000`-file stress workload is projected at `~205s` (~3.4 minutes), well within the `900s` limit.
