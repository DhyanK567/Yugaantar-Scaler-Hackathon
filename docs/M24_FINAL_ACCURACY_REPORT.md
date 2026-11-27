# MEDILOCKER M24 — FINAL ACCURACY REPORT

**Date:** 2026-11-27  
**Track:** Yugaantar DevForge — Track 3: Secret Wards

## Summary of Measurable Accuracy Improvements

1. **Unseen & Adversarial Benchmark (`tests/m24_unseen_benchmark/benchmark_m24.py`):**
   - **PII Recall:** Improved from **`0.55` (`11/20`)** to **`1.00` (`20/20`, `0` leaked)**.
   - **PII Precision / F1:** Improved from **`1.00 / 0.7097`** to **`1.00 / 1.00`**.
   - **Clinical Preservation:** Maintained **`100.0%` (`17/17`)** with `0` false modifications.
   - **Cross-Language Linking:** `Kavita Deshmukh` (English CSV) ↔ `कविता देशमुख` (Devanagari JSON) linked deterministically (`PSN-V429ZX`).
   - **Quarantine & Contract:** Malformed JSON quarantined (`1`), `validate_output.py` = `CONTRACT OK`.
2. **Engine Architecture & Classical ML Decision:**
   - Added canonical 6-layer entity representation (`starter/raksha_engine/entity_layers.py`) and generalisable Indian ID + Hinglish/Hindi context rules (`patterns.py`, `names.py`, `sanitizer.py`).
   - Retained deterministic rules + gazetteers rather than adding a CRF/ML dependency because deterministic patterns achieved `1.00` precision and `1.00` recall on the held-out/adversarial set in `< 1s` with zero extra dependencies.
3. **Verification:**
   - `tests/m24_unseen_benchmark/test_m24_regressions.py`
   - `scripts/security_regression_gate.py` (`10/10` gates)
   - `check_submission.py --repo starter --run` (`READY TO SUBMIT`)
