# M28 — CLI vs Backend vs Android Accuracy Comparison

## 1. Engine Parity Verification

`tests/android_bridge/test_android_bridge_comprehensive.py::test_cli_vs_android_bridge_parity` executed the exact same synthetic cohort (`cohort.csv`, 5 patient records) with the exact same `RAKSHA_SECRET` (`parity-secret-2026`) through:
1. **Official CLI:** `python starter/main.py --input ... --output ...`
2. **Android Bridge:** `android_api_bridge.py` (`POST /api/datasets`)

Observed parity:
- `counts.files_sanitized`: **Exact match**
- `counts.records_processed`: **Exact match** (`5`)
- `counts.identifiers_detected`: **Exact match**

---

## 2. Independent Privacy & Clinical Benchmark (`tests/independent_eval/run_independent_eval.py`)

Because the Android APK bundles and invokes the exact `starter/main.py` and `starter/raksha_engine/*` modules in-process via Chaquopy, accuracy metrics are governed by the verified core engine:

| Metric | Observed Result | Notes |
|---|---|---|
| **PII Leakage** | `0 / 10` leaked | Direct identifiers redacted/pseudonymised |
| **Canary Leakage** | `0 / 2` leaked | Synthetic canary tokens caught |
| **Clinical Fidelity** | `36 / 36` (`100.0%`) | Exact preservation of diagnoses, medications, dosages, and vitals |
| **Quarantine Enforcement** | `1 / 5` quarantined | Malformed/invalid input quarantined without crash |
| **Official Submission Contract** | `READY TO SUBMIT` (`CONTRACT OK`) | `python check_submission.py --repo starter --run` |
