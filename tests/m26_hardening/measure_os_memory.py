#!/usr/bin/env python3
"""M26 OS-Level Process Memory, CPU Affinity (2 CPUs), and Runtime Benchmark.

Measures actual Windows PeakWorkingSetSize (RSS), commit size, wall-clock time,
and CPU user+kernel time inside the real Python worker process pinned to 2 CPUs.
"""
from __future__ import annotations

import ctypes
import ctypes.wintypes as wt
import json
import os
import subprocess
import sys
import tempfile
import time
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
STARTER_DIR = REPO_ROOT / "starter"
sys.path.insert(0, str(REPO_ROOT / "tests" / "m25_adversarial_suite"))
from m25_generator import generate_large_split


_WORKER_CODE = r"""
import ctypes, ctypes.wintypes as wt, json, os, sys, time
sys.path.insert(0, sys.argv[1])

class PROCESS_MEMORY_COUNTERS(ctypes.Structure):
    _fields_ = [
        ("cb", wt.DWORD), ("PageFaultCount", wt.DWORD),
        ("PeakWorkingSetSize", ctypes.c_size_t), ("WorkingSetSize", ctypes.c_size_t),
        ("QuotaPeakPagedPoolUsage", ctypes.c_size_t), ("QuotaPagedPoolUsage", ctypes.c_size_t),
        ("QuotaPeakNonPagedPoolUsage", ctypes.c_size_t), ("QuotaNonPagedPoolUsage", ctypes.c_size_t),
        ("PagefileUsage", ctypes.c_size_t), ("PeakPagefileUsage", ctypes.c_size_t),
    ]

class FILETIME(ctypes.Structure):
    _fields_ = [("dwLowDateTime", wt.DWORD), ("dwHighDateTime", wt.DWORD)]

def ft_sec(ft):
    return ((ft.dwHighDateTime << 32) | ft.dwLowDateTime) / 10_000_000.0

k32 = ctypes.windll.kernel32
psapi = ctypes.windll.psapi
k32.GetCurrentProcess.restype = wt.HANDLE
k32.SetProcessAffinityMask.argtypes = [wt.HANDLE, ctypes.c_size_t]
k32.SetProcessAffinityMask.restype = wt.BOOL
psapi.GetProcessMemoryInfo.argtypes = [wt.HANDLE, ctypes.POINTER(PROCESS_MEMORY_COUNTERS), wt.DWORD]
psapi.GetProcessMemoryInfo.restype = wt.BOOL
k32.GetProcessTimes.argtypes = [wt.HANDLE, ctypes.POINTER(FILETIME), ctypes.POINTER(FILETIME), ctypes.POINTER(FILETIME), ctypes.POINTER(FILETIME)]
k32.GetProcessTimes.restype = wt.BOOL

h = k32.GetCurrentProcess()
k32.SetProcessAffinityMask(h, ctypes.c_size_t(0x3))

import main as starter_main
sys.argv = ["main.py", "--input", sys.argv[2], "--output", sys.argv[3]]
t0 = time.perf_counter()
starter_main.main()
wall_s = time.perf_counter() - t0

pmc = PROCESS_MEMORY_COUNTERS()
pmc.cb = ctypes.sizeof(PROCESS_MEMORY_COUNTERS)
psapi.GetProcessMemoryInfo(h, ctypes.byref(pmc), pmc.cb)

ct, et, kt, ut = FILETIME(), FILETIME(), FILETIME(), FILETIME()
k32.GetProcessTimes(h, ctypes.byref(ct), ctypes.byref(et), ctypes.byref(kt), ctypes.byref(ut))
print("M26_MEM_JSON:" + json.dumps({
    "wall_secs": round(wall_s, 3),
    "cpu_secs": round(ft_sec(ut) + ft_sec(kt), 3),
    "peak_rss_mb": round(pmc.PeakWorkingSetSize / (1024 * 1024), 2),
    "peak_commit_mb": round(pmc.PeakPagefileUsage / (1024 * 1024), 2),
    "cpu_affinity_mask": "0x3 (2 CPUs)",
}))
"""


def run_pinned_and_measure(in_dir: Path, out_dir: Path, secret: str) -> dict:
    env = os.environ.copy()
    env["RAKSHA_SECRET"] = secret
    env["HF_HUB_OFFLINE"] = "1"
    env["TRANSFORMERS_OFFLINE"] = "1"
    res = subprocess.run(
        [sys.executable, "-c", _WORKER_CODE, str(STARTER_DIR), str(in_dir), str(out_dir)],
        capture_output=True,
        text=True,
        env=env,
        check=True,
    )
    for line in res.stdout.splitlines():
        if line.startswith("M26_MEM_JSON:"):
            return json.loads(line[len("M26_MEM_JSON:"):])
    raise RuntimeError(f"Missing M26_MEM_JSON in output: {res.stdout}")


def main() -> None:
    results = {}
    for label, splits in [
        ("600_records", [("s1", 202611, 600)]),
        ("1200_records", [("s1", 202611, 600), ("s2", 202612, 600)]),
        ("2400_records", [("s1", 202611, 600), ("s2", 202612, 600), ("s3", 202613, 600), ("s4", 202614, 600)]),
    ]:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            in_dir = tmp_path / "input"
            out_dir = tmp_path / "output"
            for name, seed, n in splits:
                generate_large_split(in_dir, name, seed=seed, num_records=n)
            results[label] = run_pinned_and_measure(in_dir, out_dir, secret=f"m26-{label}")
    print(json.dumps(results, indent=2))


if __name__ == "__main__":
    main()
