#!/usr/bin/env python3
"""
Phase 6 — Automated Offline Security Regression Gate for MediLocker / GuptKavach.
Runs all mandatory security, cryptographic, clinical drift, identity, multilingual,
canary, attack simulation, determinism, and passport verification tests offline on CPU.
Exits non-zero if any check fails.
"""

import subprocess
import sys
import time
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent

GATES = [
    ("Cryptographic Assurance (HKDF, AEAD, Secret Validation)", [sys.executable, "-m", "unittest", "tests/cryptography/test_crypto_security.py"]),
    ("Clinical Fidelity & Drift Engine", [sys.executable, "-m", "unittest", "tests/clinical_drift/test_clinical_drift.py"]),
    ("Clinical Integrity & FHIR R4 Validation", [sys.executable, "-m", "unittest", "tests/clinical_integrity/test_clinical_integrity.py"]),
    ("Multilingual Contextual PII Intelligence", [sys.executable, "-m", "unittest", "tests/multilingual_intelligence/test_multilingual_intelligence.py"]),
    ("Multilingual Benchmark Evaluator", [sys.executable, "tests/multilingual/test_multilingual_pii.py"]),
    ("Live Verifiable Privacy Passport", [sys.executable, "-m", "unittest", "tests/privacy_passport_verification/test_passport_verification.py"]),
    ("Privacy Passport Core Suite", [sys.executable, "-m", "unittest", "tests/privacy_passport/test_privacy_passport.py"]),
    ("Re-Identification Attack Simulator", [sys.executable, "-m", "unittest", "tests/privacy_attacks/test_privacy_attacks.py"]),
    ("End-to-End Pipeline & Determinism", [sys.executable, "-m", "unittest", "tests/integration/test_full_pipeline_integration.py"]),
    ("Dataset Workflow E2E", [sys.executable, "-m", "unittest", "tests/integration/test_dataset_workflow_e2e.py"]),
]


def main() -> int:
    print("=" * 72)
    print("MEDILOCKER / GUPTKAVACH — AUTOMATED SECURITY REGRESSION GATE")
    print("=" * 72)
    t0 = time.perf_counter()
    failed = []

    for label, cmd in GATES:
        print(f"\n[GATE] {label} ...")
        res = subprocess.run(cmd, cwd=str(REPO_ROOT), capture_output=True, text=True)
        if res.returncode != 0:
            print(f"  [FAIL] {label}")
            print(res.stdout[-500:] if res.stdout else "")
            print(res.stderr[-500:] if res.stderr else "")
            failed.append(label)
        else:
            print(f"  [PASS] {label}")

    elapsed = time.perf_counter() - t0
    print("\n" + "=" * 72)
    if failed:
        print(f"GATE STATUS: BLOCKED ({len(failed)}/{len(GATES)} gates failed) in {elapsed:.2f}s")
        for f in failed:
            print(f"  - {f}")
        print("=" * 72)
        return 1

    print(f"GATE STATUS: PASSED ({len(GATES)}/{len(GATES)} gates passed) in {elapsed:.2f}s")
    print("=" * 72)
    return 0


if __name__ == "__main__":
    sys.exit(main())
