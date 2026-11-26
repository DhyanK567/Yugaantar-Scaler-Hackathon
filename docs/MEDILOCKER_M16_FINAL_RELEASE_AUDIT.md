# MEDILOCKER M16.4 — FINAL RELEASE CANDIDATE VERIFICATION AUDIT

**Audit Date:** 2026-11-27  
**Track:** Yugaantar DevForge Hackathon — Track 3: Secret Wards  
**Auditor Role:** Independent Hackathon Submission Auditor  
**Target Branch / Commit:** `mailestone-15.5` at `205d30e` (`Merge pull request #21 from DhyanK567/milestone-8/security-audit`, equal to `origin/main`)

---

## Final Release Decision

**CONDITIONALLY READY**

The standalone Track 3 privacy engine (`starter/main.py`), official output contract (`validate_output.py`), official dev benchmark (`check_dev.py` with **0 / 3,230** PII leaks and **0.0%** filename leakage), root submission checker (`check_submission.py --repo . --run`), 10-gate security regression suite (`scripts/security_regression_gate.py`), independent held-out evaluation, and Next.js production build all pass cleanly.

However, **READY FOR SUBMISSION** cannot be issued unconditionally because:
1. `starter/raksha.toml` invokes `python main.py` instead of `python3 main.py`, causing `python3 check_submission.py --repo starter --run` and `bash scripts/verify_submission.sh` to **FAIL** (exit code `1` / `127: python: not found`) on `python3`-only Linux environments.
2. `README.md` Section 9 reports stale Milestone 14 benchmark numbers (`1.1%` leaked, `4,449 / 4,457`, `R=0.76`) that contradict the current verified run (`0.0%` leaked, `4,847 / 4,855`, `R=0.81`).
3. `tests/pdf_reporting/test_pdf_reporting.py` has **1 failing test** (`test_01_all_five_operational_pdfs_generate_and_contain_expected_fields`).
4. `data/guptkavach.db-shm` and `data/guptkavach.db-wal` are tracked in Git on `origin/main`, causing working-tree churn (`D` status) when SQLite runs in WAL mode.
5. `pytest` and `httpx` are not installed in the system Python (`3.14.4`), blocking execution of `tests/milestone_17/test_milestone_17.py`, `tests/milestone_18/test_offline_verification.py`, `tests/integration/test_full_app_e2e.py`, and `test_guptkavach_system.py` in this environment.

---

## 1. Repository Integrity Inspection

| Item | Observed State | Status | Notes |
|---|---|---|---|
| **Git Branch & Commit** | `mailestone-15.5` at `205d30e` (`== origin/main`, 25 commits ahead of `origin/mailestone-15.5`) | VERIFIED | `git diff --name-only origin/main..HEAD` is empty. |
| **Working Tree** | `D data/guptkavach.db-shm`, `D data/guptkavach.db-wal` | PARTIALLY VERIFIED | Runtime SQLite WAL files are tracked in Git on `origin/main`. |
| **Official Toolkit Files** | `validate_output.py`, `check_dev.py`, `check_submission.py`, `START_HERE.md`, `scoring.toml` present and unmodified | VERIFIED | Official scripts preserved. |
| **Root Submission Config** | `raksha.toml` (`Team Halfwave`, `python3 starter/main.py --input {input} --output {output}`), `requirements.txt`, `config/policy.yaml` | VERIFIED | Passes `check_submission.py --repo . --run`. |
| **Starter Submission Config** | `starter/raksha.toml` (`run = "python main.py --input {input} --output {output}"`) | FAILED | Fails on `python3`-only Linux systems (`python: not found`). |
| **Project Brief PDFs** | `submission/MediLocker_Project_Brief.pdf` (2 pages A4, 120,232 B); `starter/GuptKavach_Project_Brief.pdf` (2 pages A4, 8,304 B); `docs/GuptKavach_Project_Brief.pdf` (2 pages A4, 8,304 B) | VERIFIED | All 3 briefs are 2-page A4 PDFs; `submission/MediLocker_Project_Brief.pdf` matches current `0/3,230`, `4,847/4,855`, `P=1.00, R=0.81, F0.5=0.95` numbers. |
| **README Instructions** | `README.md` documents one-click verification, CLI evaluator, and API | PARTIALLY VERIFIED | `bash scripts/verify_submission.sh` fails on `check_submission --repo starter --run`, and Section 9 metrics are stale. |

---

## 2. Complete Verification Results (Clean Output Directory `/tmp/m16_4_clean_out`)

| # | Check | Status | Exact Command | Exit Code | Measured Result | Evidence Path | Remaining Risk | Blocks Submission? |
|---|---|---|---|---|---|---|---|---|
| 1 | **Filename Privacy Regression** | **VERIFIED** | `python3 check_dev.py --output /tmp/m16_4_clean_out --show 10` | `0` | `by hiding place: filename 0.0%` (`0` filename leaks) | `dev/input` -> `/tmp/m16_4_clean_out/sanitized/` | None on `dev/input` | No |
| 2 | **Official Development Benchmark** | **VERIFIED** | `RAKSHA_SECRET=m16-4-audit-secret python3 starter/main.py --input dev/input --output /tmp/m16_4_clean_out && python3 check_dev.py --output /tmp/m16_4_clean_out --show 10` | `0` | `0 / 3,230 (0.0%)` PII leaked across all 16 types, 3 scripts (`latin/deva/hinglish 0.0%`), 6 hiding places; `0 / 4` canaries; `4,847 / 4,855 (99.8%)` medical kept; Linking `P=1.00, R=0.81, F0.5=0.95` (`0` false merges); `0` raw copies | `/tmp/m16_4_clean_out` | Synthetic practice data only; real-world unseen data may contain novel formats | No |
| 3 | **Official Output Validator** | **VERIFIED** | `python3 validate_output.py --input dev/input --output /tmp/m16_4_clean_out` | `0` | `CONTRACT OK` (`files 200 sanitized 195 quarantined 5 records 823`) | `/tmp/m16_4_clean_out/report.json`, `records.jsonl` | None | No |
| 4 | **Independent Held-Out Evaluation** | **VERIFIED** | `python3 tests/independent_eval/run_independent_eval.py` | `0` | `direct_pii_leaked: 0/10`, `canaries_leaked: 0/2`, `post_uniquely_distinguishable: 0` (from `6`), `clinical: 36/36 (100.0%)`, `files_total: 5` (`4 sanitized, 1 quarantined`), `runtime_secs: 0.117`, `peak_rss_mb: 30.55`, `release_decision: PASS` | `tests/independent_eval/run_independent_eval.py` | Small synthetic held-out corpus (`5` files, `8` records) | No |
| 5 | **Cryptographic Tests** | **VERIFIED** | `python3 -m unittest tests/cryptography/test_crypto_security.py` (via `security_regression_gate.py`) | `0` | `16 / 16` tests passed (`HKDF-SHA256`, AEAD, secret validation) | `tests/cryptography/test_crypto_security.py` | Requires `cryptography>=41.0` | No |
| 6 | **Clinical Fidelity & Drift Tests** | **VERIFIED** | `python3 -m unittest tests/clinical_drift/test_clinical_drift.py` | `0` | `5 / 5` tests passed | `tests/clinical_drift/test_clinical_drift.py` | Regex-based 15-category clinical extraction | No |
| 7 | **FHIR R4 & Clinical Integrity** | **VERIFIED** | `python3 -m unittest tests/clinical_integrity/test_clinical_integrity.py` | `0` | `9 / 9` tests passed | `tests/clinical_integrity/test_clinical_integrity.py` | None | No |
| 8 | **Multilingual PII Tests** | **VERIFIED** | `python3 tests/multilingual/test_multilingual_pii.py` & `python3 -m unittest tests/multilingual_intelligence/test_multilingual_intelligence.py` | `0` | `18 / 18` cases (`P=1.000, R=1.000, F1=1.000, Safe Preserved 30/30 (100.0%)`) + contextual suite PASS | `tests/multilingual/test_multilingual_pii.py` | Limited to covered English/Hindi/Hinglish patterns | No |
| 9 | **Identity Continuity Tests** | **VERIFIED** | `python3 tests/identity_adversarial/run_identity_benchmark.py` | `0` | `29` records: `P=1.0, R=1.0, F0.5=1.0, false_merges=0, abstentions=2`, `Order invariance: True`, `Cross-secret collisions: 0` | `tests/identity_adversarial/run_identity_benchmark.py` | Synthetic adversarial set | No |
| 10 | **Privacy Passport Tamper Verification** | **VERIFIED** | `python3 -m unittest tests/privacy_passport/test_privacy_passport.py` & `tests/privacy_passport_verification/test_passport_verification.py` | `0` | `19 / 19` core tests + live verification suite PASS | `tests/privacy_passport/test_privacy_passport.py` | Default `UNSIGNED` unless Ed25519 key env var is set | No |
| 11 | **Re-Identification Attack Simulator** | **VERIFIED** | `python3 -m unittest tests/privacy_attacks/test_privacy_attacks.py` | `0` | `10 / 10` tests passed | `tests/privacy_attacks/test_privacy_attacks.py` | Covers modeled deterministic attack vectors | No |
| 12 | **Authentication & Org-Scoping Tests** | **BLOCKED** | `python3 -m pytest tests/milestone_17/test_milestone_17.py tests/milestone_18/test_offline_verification.py -v` | `1` | `No module named pytest` in `/usr/bin/python3` | `tests/milestone_17/`, `tests/milestone_18/` | Not verified in this audit run due to missing `pytest` | No (web-only; not Track 3 CLI) |
| 13 | **Security Regression Gate** | **VERIFIED** | `python3 scripts/security_regression_gate.py` | `0` | `GATE STATUS: PASSED (10/10 gates passed) in 3.18s` | `scripts/security_regression_gate.py` | None | No |
| 14 | **Legacy System Test & Full App E2E** | **BLOCKED** | `python3 test_guptkavach_system.py` & `python3 -m unittest tests/integration/test_full_app_e2e.py` | `1` | `RuntimeError: The starlette.testclient module requires the httpx package` | `test_guptkavach_system.py`, `tests/integration/test_full_app_e2e.py` | Missing `httpx` in system Python | No (web-only) |
| 15 | **PDF Reporting Tests** | **FAILED** | `python3 -m unittest tests/pdf_reporting/test_pdf_reporting.py` | `1` | `4` passed, `1` failed (`test_01`: `'APPROVED'` not found; PDF printed raw dict `{'status': 'PASS_WITH_WARNINGS', ...}`) | `tests/pdf_reporting/test_pdf_reporting.py` | Raw dict string rendered in operational PDF | No (web/reporting only) |
| 16 | **Frontend Production Build** | **VERIFIED** | `cd frontend && pnpm build` | `0` | `22 / 22` routes compiled cleanly (static prerendered) | `frontend/.next` | None | No |
| 17 | **Official Submission Checker (Root)** | **VERIFIED** | `python3 check_submission.py --repo . --run` | `0` | `READY TO SUBMIT` (`0.9s`, `CONTRACT OK`, deterministic, secret-safe) | `raksha.toml` | Depends on root `raksha.toml` | No |
| 18 | **Official Submission Checker (Starter) & One-Click Script** | **FAILED** | `python3 check_submission.py --repo starter --run` & `bash scripts/verify_submission.sh` | `1` | Exit `127`: `/bin/sh: 1: python: not found` (`starter/raksha.toml` uses `python` instead of `python3`) | `starter/raksha.toml`, `scripts/verify_submission.sh` | Fails if evaluator runs `--repo starter` on `python3`-only Linux | **Yes** (if evaluator targets `starter/`) |

---

## 3. Offline & Determinism Verification

- **Exact Command:** Subprocess execution of `starter/main.py --input dev/input --output <out>` twice with `HF_HUB_OFFLINE=1`, `TRANSFORMERS_OFFLINE=1`, `NO_PROXY=*`, `HTTP_PROXY=""`, `HTTPS_PROXY=""`, `RAKSHA_SECRET=offline-audit-secret-key-999`, and `socket.socket.connect` monkeypatched to raise `OSError("OFFLINE_AUDIT_BLOCKED_SOCKET")`.
- **Exit Code:** `0` on both runs (`files 200 sanitized 195 quarantined 5 records 823`).
- **Determinism:** `199 / 199` non-`report.json` output files (`sanitized/` + `records.jsonl`) were byte-identical (SHA-256) across both runs.
- **Zero External AI / LLMs / Network:** Confirmed `starter/requirements.txt` contains only `cryptography>=41.0` (no `openai`, `anthropic`, `transformers`, `torch`, or hosted AI SDKs), CPU-only execution.
- **No PII / Secrets in Logs:** `offline-audit-secret-key-999` did not appear in stdout or stderr; `check_dev.py` confirmed `0` raw copies in `sanitized/`.
- **Status:** **VERIFIED**

---

## 4. Submission Consistency Cross-Check

| Document | Claimed Dev Benchmark Metrics | Matches Current Run (`205d30e`)? | Notes |
|---|---|---|---|
| **Current Verified Run (`dev/input`)** | `0/3,230 (0.0%)` leaks, `0/4` canaries, `4,847/4,855 (99.8%)` medical, `P=1.00, R=0.81, F0.5=0.95` | Baseline | Measured in this audit. |
| `submission/MediLocker_Project_Brief.pdf` | `0 / 3,230 (0.0%)`, `4,847 / 4,855 (99.8%)`, `P=1.00, R=0.81, F0.5=0.95` | **YES** | Accurate 2-page A4 PDF. |
| `docs/MILESTONE_15_5_REPORT.md` & `docs/MILESTONE_15_5_BASELINE.md` | `0 / 3,230 (0.0%)`, `4,847 / 4,855 (99.8%)`, `P=1.00, R=0.81, F0.5=0.95`; Held-out eval `0/10` PII, `36/36 (100.0%)` | **YES** | Held-out evaluation clearly separated from `dev/input`. |
| `README.md` (Section 9) | `1.1%` leaked, `4,449 / 4,457 (99.8%)` medical, `P=1.00 / R=0.76 / F0.5=0.94` | **NO (Stale)** | Reflects older Milestone 14 run, not `205d30e`. |
| `docs/MEDILOCKER_FINAL_READINESS_AUDIT.md` & `docs/MEDILOCKER_END_TO_END_AUDIT.md` | `35 / 3,230 (1.1%)` filename leaks, `4,449 / 4,457`, `R=0.76, F0.5=0.94` | **NO (Historical)** | Audited against `6d3f49e` before filename-leak fix in `205d30e`. |

> **Scope Caveat:** `0 / 3,230` direct PII leakage on `dev/input` and `0 / 10` on `tests/independent_eval/` apply strictly to those synthetic test corpora and do **not** guarantee zero re-identification risk on arbitrary unseen real-world datasets.

---

## 5. Fresh-Clone Reproducibility Test

- **Command:** `git worktree add --detach /tmp/m16_4_worktree HEAD` (clean `205d30e` checkout without local untracked files), followed by:
  - `RAKSHA_SECRET=practice python3 starter/main.py --input dev/input --output /tmp/m16_4_wt_out` -> Exit `0` (`files 200 sanitized 195 quarantined 5 records 823`)
  - `python3 validate_output.py --input dev/input --output /tmp/m16_4_wt_out` -> Exit `0` (`CONTRACT OK`)
  - `python3 check_dev.py --output /tmp/m16_4_wt_out` -> Exit `0` (`0 / 3,230` leaks, `0 / 4` canaries, `4,847 / 4,855` medical, `P=1.00, R=0.81, F0.5=0.95`)
  - `python3 check_submission.py --repo . --run` -> Exit `0` (`READY TO SUBMIT`)
  - `python3 check_submission.py --repo starter --run` -> Exit `1` (`/bin/sh: 1: python: not found`)
- **Status:** **PARTIALLY VERIFIED** (root repo passes from clean checkout; `starter/` sub-repo fails `--run` without `python` symlink).

---

## 6. Recommended Actions Before Final Submission

1. Update `starter/raksha.toml` `run` command from `python main.py ...` to `python3 main.py ...` (so `check_submission.py --repo starter --run` and `bash scripts/verify_submission.sh` pass on Linux).
2. Update `README.md` Section 9 benchmark table to match `205d30e` (`0 / 3,230`, `4,847 / 4,855`, `P=1.00, R=0.81, F0.5=0.95`).
3. Remove `data/guptkavach.db-shm` and `data/guptkavach.db-wal` from Git tracking (`git rm --cached`) and keep them in `.gitignore`.
4. Fix `backend/services/pdf_reporting/` formatting of `release_decision` (string status instead of raw dict) so `tests/pdf_reporting/test_pdf_reporting.py` passes `5/5`.
