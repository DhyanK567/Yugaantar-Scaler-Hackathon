"""M14.7 & M14.8: Load, Stress, Memory, Determinism & Fault-Tolerance Benchmark Suite."""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import time
import tracemalloc
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
PERF_DIR = Path(__file__).resolve().parent


def _generate_synthetic_tier(inp_dir: Path, n_files: int) -> None:
    if inp_dir.exists():
        shutil.rmtree(inp_dir)
    (inp_dir / "reg").mkdir(parents=True)
    (inp_dir / "notes").mkdir(parents=True)
    (inp_dir / "opd").mkdir(parents=True)
    (inp_dir / "misc").mkdir(parents=True)

    for i in range(n_files):
        kind = i % 4
        pid = i % max(10, n_files // 5)
        phone = f"98{10000000 + pid:08d}"
        if kind == 0:
            (inp_dir / "reg" / f"reg_{i:05d}.csv").write_text(
                "UHID,Patient Name,Gender,Age,District,PIN,Mobile\n"
                f"KMC/26/{100000+pid},Synthetic Patient {pid},M,{25 + (pid % 50)},Lucknow,226010,{phone}\n"
                f"KMC/26/{200000+pid},Synthetic Patient {pid+1},F,{30 + (pid % 40)},Unnao,209801,98{20000000 + pid:08d}\n",
                encoding="utf-8",
            )
        elif kind == 1:
            (inp_dir / "notes" / f"note_{i:05d}.txt").write_text(
                f"Patient: Synthetic Patient {pid}\n"
                f"Mobile: {phone}\n"
                "C/O fever x 3 days. Rx: Dolo 650 BD x 5 days.\n"
                "Dr. Ramesh reviewed the patient.\n",
                encoding="utf-8",
            )
        elif kind == 2:
            obj = {
                "visits": [
                    {
                        "visit_id": f"OPD/26/{i:05d}",
                        "patient_ref": f"KMC/26/{100000+pid}",
                        "complaints": "C/O cough",
                        "rx": [{"drug": "Azithromycin", "strength": "500 mg", "frequency": "1-0-0"}],
                    }
                ]
            }
            (inp_dir / "opd" / f"opd_{i:05d}.json").write_text(json.dumps(obj), encoding="utf-8")
        else:
            if i % 40 == 3:
                # Malformed JSON -> must be quarantined
                (inp_dir / "misc" / f"bad_{i:05d}.json").write_text('{"broken": ', encoding="utf-8")
            else:
                (inp_dir / "notes" / f"rx_{i:05d}.txt").write_text(
                    f"नाम: मरीज {pid}   आयु: {20 + (pid % 60)} वर्ष\n"
                    "Tab Paracetamol 650 mg 1-1-1 x 5 days\n",
                    encoding="utf-8",
                )


def _run_tier(name: str, inp_dir: Path, out_dir: Path) -> dict:
    if out_dir.exists():
        shutil.rmtree(out_dir)
    env = dict(os.environ, RAKSHA_SECRET="perf_bench_secret")
    t0 = time.monotonic()
    proc = subprocess.run(
        [sys.executable, str(REPO_ROOT / "starter" / "main.py"), "--input", str(inp_dir), "--output", str(out_dir)],
        env=env,
        capture_output=True,
        text=True,
    )
    wall = time.monotonic() - t0
    rep = json.loads((out_dir / "report.json").read_text(encoding="utf-8"))
    c = rep["counts"]
    return {
        "tier": name,
        "exit_code": proc.returncode,
        "wall_s": round(wall, 2),
        "files_total": c["files_total"],
        "files_sanitized": c["files_sanitized"],
        "files_quarantined": c["files_quarantined"],
        "records_processed": c["records_processed"],
        "files_per_sec": round(c["files_total"] / max(0.01, wall), 1),
        "records_per_sec": round(c["records_processed"] / max(0.01, wall), 1),
    }


def _fault_tolerance_checks() -> dict:
    # 1. Corrupt / unsupported / empty batch
    ft_inp = PERF_DIR / "ft_input"
    ft_out = PERF_DIR / "ft_output"
    for d in (ft_inp, ft_out):
        if d.exists():
            shutil.rmtree(d)
    ft_inp.mkdir(parents=True)
    (ft_inp / "bad.json").write_text("{corrupt", encoding="utf-8")
    (ft_inp / "empty.csv").write_text("", encoding="utf-8")
    (ft_inp / "raw.pdf").write_bytes(b"%PDF-1.4\nRaw PII Rajesh Kumar")
    (ft_inp / "ok.txt").write_text("Patient: Test User\nDolo 650 mg\n", encoding="utf-8")

    env = dict(os.environ, RAKSHA_SECRET="ft_secret")
    p1 = subprocess.run([sys.executable, str(REPO_ROOT / "starter" / "main.py"), "--input", str(ft_inp), "--output", str(ft_out)], env=env, capture_output=True, text=True)
    # Rerun on same output dir (recovery without duplicate records)
    p2 = subprocess.run([sys.executable, str(REPO_ROOT / "starter" / "main.py"), "--input", str(ft_inp), "--output", str(ft_out)], env=env, capture_output=True, text=True)
    rep = json.loads((ft_out / "report.json").read_text(encoding="utf-8"))
    recs = [l for l in (ft_out / "records.jsonl").read_text(encoding="utf-8").splitlines() if l.strip()]
    raw_in_sanitized = (ft_out / "sanitized" / "raw.pdf").exists() or (ft_out / "sanitized" / "bad.json").exists()
    shutil.rmtree(ft_inp)
    shutil.rmtree(ft_out)
    return {
        "exit_codes": [p1.returncode, p2.returncode],
        "quarantined": rep["counts"]["files_quarantined"],
        "sanitized": rep["counts"]["files_sanitized"],
        "records_after_rerun": len(recs),
        "raw_leaked_into_sanitized": raw_in_sanitized,
    }


def main() -> int:
    results = []
    # Small: official 200-file dev/input
    results.append(_run_tier("Small (200 files, dev/input)", REPO_ROOT / "dev" / "input", PERF_DIR / "out_small"))

    # Medium: 1,000 files
    med_inp = PERF_DIR / "in_medium"
    _generate_synthetic_tier(med_inp, 1000)
    results.append(_run_tier("Medium (1,000 synthetic)", med_inp, PERF_DIR / "out_medium"))
    shutil.rmtree(med_inp)

    # Large: 5,000 files
    lg_inp = PERF_DIR / "in_large"
    _generate_synthetic_tier(lg_inp, 5000)
    results.append(_run_tier("Large (5,000 synthetic)", lg_inp, PERF_DIR / "out_large"))
    shutil.rmtree(lg_inp)

    # Fault tolerance
    ft = _fault_tolerance_checks()

    # Clean up generated output dirs
    for d in ("out_small", "out_medium", "out_large"):
        p = PERF_DIR / d
        if p.exists():
            shutil.rmtree(p)

    print("=== M14.8 LOAD & FAULT-TOLERANCE BENCHMARKS ===")
    for r in results:
        print(json.dumps(r))
    print("FAULT_TOLERANCE:", json.dumps(ft))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
