# MEDILOCKER M26 — REGRESSION SAFETY REPORT

**Date:** 2026-11-27

## Verified Post-Change Suites (Zero Failures, Zero Skips)

| Suite / Gate | Command | Observed Result |
| :--- | :--- | :--- |
| **M24 + M25 + M26 Regressions** | `.\.venv\Scripts\python.exe -m pytest tests/m24_unseen_benchmark/test_m24_regressions.py tests/m25_adversarial_suite/test_m25_regressions.py tests/m26_hardening/test_m26_suite.py -v` | **`9 passed in 15.00s`** |
| **Security Regression Gate** | `.\.venv\Scripts\python.exe scripts/security_regression_gate.py` | **`GATE STATUS: PASSED (10/10 gates passed) in 29.07s`** |
| **Official Submission Checker** | `.\.venv\Scripts\python.exe check_submission.py --repo starter --run` | **`READY TO SUBMIT` (`9.8s`, `CONTRACT OK`, exit code `0`)** |
| **Development Benchmark (`check_dev.py`, exact SHA)** | `check_dev.py --output <out>` | **`0/3,230` leaked (`0.0%`), `0/4` canaries, `4,847/4,855` (`99.8%`) clinical, `P=1.00, R=0.81, F0.5=0.95, FP=0`** |
