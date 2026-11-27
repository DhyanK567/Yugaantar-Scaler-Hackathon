# MEDILOCKER M24 — IDENTITY LINKING EVALUATION

- **Conservative Multi-Signal Resolution (`starter/raksha_engine/linking.py`):** Uses strong IDs (`Aadhaar`, `ABHA`, `PAN`, `phone`), hospital-scoped MRNs, Devanagari/Hinglish phonetic normalization, and demographic conflict guards.
- **Unseen Cross-Language Result:** Successfully linked English CSV `Kavita Deshmukh` and Devanagari nested JSON `कविता देशमुख` under identical deterministic pseudonym `PSN-V429ZX`.
- **Official `dev/input` Result (`check_dev.py`):** `precision 1.00, recall 0.76, F0.5 0.94` with **`0` false merges**.
