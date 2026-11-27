# MEDILOCKER M24 — PERFORMANCE REPORT

- **Unseen & Adversarial Benchmark (`6` files, multi-format):** `0.994s` wall-clock runtime (well within 15-minute / 900s limit).
- **Independent Eval (`5` files, `8` records):** `0.991s` runtime, `29.68 MB` peak RSS (well within 4 GB RAM / 2 CPU limit).
- **Official Submission Checker (`dev/input`, `200` files, `823` records, 3 runs):** `11.0s` total (`~3.7s` per run), `CONTRACT OK`.
- **Resource Footprint:** Pure Python stdlib (`starter/main.py`), CPU-only, zero GPU/LLM/model loading overhead.
