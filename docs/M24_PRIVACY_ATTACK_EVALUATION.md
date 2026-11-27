# MEDILOCKER M24 — PRIVACY ATTACK EVALUATION

- **Canary Leakage:** `0 / 2` leaked on unseen/adversarial benchmark; `0 / 2` leaked on `independent_eval`; `0 / 4` leaked on `dev/input`.
- **Re-Identification Attack Simulator (`tests/privacy_attacks/test_privacy_attacks.py`):** Passed in `scripts/security_regression_gate.py` (`10/10` gates).
- **Quasi-Identifier Mitigation:** 5-year age banding, `±180`-day keyed date shifting, PIN prefixing, and rare-combination suppression under `min_group_size: 5` (`config/policy.yaml`).
- **Boundary:** Risk mitigation reduces singling-out and linkage risk under configured quasi-identifiers; it does not claim formal $(\varepsilon, \delta)$-differential privacy.
