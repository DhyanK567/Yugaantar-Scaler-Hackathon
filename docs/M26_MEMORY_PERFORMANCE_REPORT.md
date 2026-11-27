# MEDILOCKER M26 — REAL PROCESS MEMORY & PERFORMANCE REPORT

**Date:** 2026-11-27  
**Measurement Script:** `tests/m26_hardening/measure_os_memory.py`

## 1. Methodology (OS-Level RSS & 2-CPU Affinity)

Executed `starter/main.py` inside a dedicated child Python worker process pinned to **2 CPU cores** (`SetProcessAffinityMask(..., 0x3)`) with `HF_HUB_OFFLINE=1` and `TRANSFORMERS_OFFLINE=1`, measuring Windows `PROCESS_MEMORY_COUNTERS.PeakWorkingSetSize` (RSS), `PeakPagefileUsage` (commit), `GetProcessTimes` (user + kernel CPU time), and wall-clock time.

## 2. Observed Resource Measurements

| Batch Size | CPU Affinity | Wall Time | CPU Time (User+Kernel) | Peak OS RSS (`PeakWorkingSetSize`) | Peak Commit |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **`600` records** | `0x3` (`2` CPUs) | `4.573s` | `3.828s` | **`32.14 MB`** | `22.83 MB` |
| **`1,200` records** | `0x3` (`2` CPUs) | `9.470s` | `7.094s` | **`35.68 MB`** | `25.90 MB` |
| **`2,400` records** | `0x3` (`2` CPUs) | `20.617s` | `14.891s` | **`42.62 MB`** | `33.23 MB` |

## 3. Compliance Against Official Limits (`2` CPUs / `4 GB` RAM / `15` Minutes)

- **Peak RSS (`42.62 MB` at `2,400` records):** Uses **`1.04%`** of the `4,096 MB` (`4 GB`) RAM budget.
- **Wall Time (`20.617s` at `2,400` records):** Uses **`2.29%`** of the `900s` (`15`-minute) budget.
