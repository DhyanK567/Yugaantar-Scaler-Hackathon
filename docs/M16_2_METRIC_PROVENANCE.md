# M16.2 — Clinical Fidelity & Identity Metric Provenance

## 1. Objective
Reconcile the metric discrepancy between:
- **Milestone 15.5 Report (`docs/MILESTONE_15_5_REPORT.md`)**: `4,847 / 4,855` clinical values preserved, `P=1.00, R=0.81, F0.5=0.95`, `0 / 3,230` leaks.
- **Latest Audit Docs (`docs/MEDILOCKER_FINAL_READINESS_AUDIT.md`, `docs/MEDILOCKER_END_TO_END_AUDIT.md`)**: `4,449 / 4,457` clinical values preserved, `P=1.00, R=0.76, F0.5=0.94`, `35 / 3,230` filename leaks.

---

## 2. Clean-Room Reproduction on Current `HEAD`
- **Input Dataset**: `dev/input` (`200` files)
- **Ground Truth**: `dev/truth/truth.json` (`200` files, `4,855` `preserve` items, `771` `link="required"` units, `6,892` true identity pairs)
- **Command**:
  ```powershell
  $env:RAKSHA_SECRET="m16-2-repro-secret-2026"
  python starter/main.py --input dev/input --output <clean_out>
  python check_dev.py --output <clean_out>
  python validate_output.py --input dev/input --output <clean_out>
  ```
- **Reproduced Counts**:
  - Files: `200` total, `195` sanitized, `5` quarantined, `823` records in `records.jsonl`
  - PII leaked: `0 / 3,230 (0.0%)` (content `0.0%`, filename `0.0%`, base64 `0.0%`, metadata `0.0%`, key `0.0%`, header `0.0%`)
  - Canaries leaked: `0 / 4`
  - Clinical values preserved: **`4,847 / 4,855 (99.8%)`**, missing = `8`, modified = `0`
  - Identity linking: **`tp = 5,551`, `fp = 0`, `fn = 1,341`, `true_pairs = 6,892`** -> **Precision `1.0000` (`1.00`)**, **Recall `0.8054` (`0.81`)**, **F0.5 `0.9539` (`0.95`)**, **False merges = `0`**
  - Raw copies: `0`

---

## 3. Root Cause of the Discrepancy (`4,847 / 4,855` vs `4,449 / 4,457`)
1. **Different benchmark/engine snapshot**: `docs/MEDILOCKER_FINAL_READINESS_AUDIT.md` and `docs/MEDILOCKER_END_TO_END_AUDIT.md` were generated on an earlier snapshot where `check_dev.py` evaluated `4,457` `preserve` items (398 fewer than the `4,855` items in current `dev/truth/truth.json`) and had not yet included the `sanitize_filename()` fix (`35 / 3,230` filename leaks).
2. **Identical missing count (`8`)**: Both snapshots have **exactly 8 missing clinical values** (`4,855 - 4,847 = 8` and `4,457 - 4,449 = 8`), confirming both represent the same 8 suppressed rare `district` cells in `registration/arogya_legacy_export.csv`.
3. **`docs/MILESTONE_15_5_REPORT.md` is confirmed accurate** against current `dev/input` and `dev/truth/truth.json` (`4,847 / 4,855`, `R=0.81`, `F0.5=0.95`, `0 / 3,230` leaks).
