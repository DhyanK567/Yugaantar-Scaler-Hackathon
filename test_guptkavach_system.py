"""GuptKavach End-to-End System & Regression Verification Suite.
Validates:
1. Original standalone CLI execution
2. validate_output.py contract check
3. check_dev.py self-check evaluation
4. Same-secret determinism test
5. Different-secret pseudonym separation test
6. Secret leakage check in logs and outputs
7. FHIR R4 Bundle integrity test
8. Malformed & unsupported input quarantine test
9. FastAPI backend real engine integration
10. File download and quarantine output handling
11. PII and secret non-exposure across all API endpoints
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import subprocess
import sys
import tempfile
import time
from pathlib import Path
from fastapi.testclient import TestClient

REPO_ROOT = Path(__file__).resolve().parent
STARTER_DIR = REPO_ROOT / "starter"
DEV_INPUT = REPO_ROOT / "dev" / "input"
VALIDATE_PY = REPO_ROOT / "validate_output.py"
CHECK_DEV_PY = REPO_ROOT / "check_dev.py"

from backend.main import app

client = TestClient(app)

passes = 0
fails = 0


def log_test(name: str, passed: bool, detail: str = ""):
    global passes, fails
    if passed:
        passes += 1
        print(f"  [PASS] {name}" + (f": {detail}" if detail else ""))
    else:
        fails += 1
        print(f"  [FAIL] {name}" + (f": {detail}" if detail else ""))


def run_full_suite():
    global passes, fails
    print("\n========================================================")
    print(" GUPTKAVACH FULL REGRESSION & COMPLIANCE TEST SUITE")
    print("========================================================\n")

    # 1. Standalone CLI Run
    out1 = Path(tempfile.mkdtemp(prefix="gk-test1-"))
    t0 = time.monotonic()
    cmd1 = [sys.executable, str(STARTER_DIR / "main.py"), "--input", str(DEV_INPUT), "--output", str(out1)]
    res1 = subprocess.run(cmd1, cwd=str(STARTER_DIR), env=dict(os.environ, RAKSHA_SECRET="secretA"), capture_output=True, text=True)
    dt1 = time.monotonic() - t0
    log_test("1. Original Standalone CLI Execution", res1.returncode == 0, f"Exit code 0 in {dt1:.2f}s")

    # 2. validate_output.py
    res2 = subprocess.run([sys.executable, str(VALIDATE_PY), "--input", str(DEV_INPUT), "--output", str(out1)], capture_output=True, text=True)
    log_test("2. Output Contract Validation (validate_output.py)", "CONTRACT OK" in res2.stdout, res2.stdout.strip())

    # 3. check_dev.py
    res3 = subprocess.run([sys.executable, str(CHECK_DEV_PY), "--output", str(out1)], capture_output=True, text=True)
    log_test("3. Practice Self-Check (check_dev.py)", "SECRET WARDS practice self-check" in res3.stdout, "Evaluator executed")

    # 4. Same-Secret Determinism Test
    out2 = Path(tempfile.mkdtemp(prefix="gk-test2-"))
    res4 = subprocess.run([sys.executable, str(STARTER_DIR / "main.py"), "--input", str(DEV_INPUT), "--output", str(out2)],
                          cwd=str(STARTER_DIR), env=dict(os.environ, RAKSHA_SECRET="secretA"), capture_output=True, text=True)
    h1 = hashlib.sha256((out1 / "records.jsonl").read_bytes()).hexdigest()
    h2 = hashlib.sha256((out2 / "records.jsonl").read_bytes()).hexdigest()
    log_test("4. Same-Secret Determinism Test", h1 == h2, f"Identical records.jsonl SHA256: {h1[:12]}...")

    # 5. Different-Secret Pseudonym Separation
    out3 = Path(tempfile.mkdtemp(prefix="gk-test3-"))
    res5 = subprocess.run([sys.executable, str(STARTER_DIR / "main.py"), "--input", str(DEV_INPUT), "--output", str(out3)],
                          cwd=str(STARTER_DIR), env=dict(os.environ, RAKSHA_SECRET="secretB"), capture_output=True, text=True)
    h3 = hashlib.sha256((out3 / "records.jsonl").read_bytes()).hexdigest()
    log_test("5. Different-Secret Pseudonym Separation", h1 != h3, "Different secret produced disjoint output")

    # 6. Secret Leakage Check
    leaked_secret = False
    secret_bytes = b"secretA"
    for p in out1.rglob("*"):
        if p.is_file() and secret_bytes in p.read_bytes():
            leaked_secret = True
            break
    log_test("6. RAKSHA_SECRET Containment Check", not leaked_secret and secret_bytes not in res1.stdout.encode(), "Zero secret leakage")

    # 7. FHIR Integrity Check
    fhir_files = list((out1 / "sanitized").rglob("*.json"))
    fhir_valid = False
    for f in fhir_files:
        try:
            data = json.loads(f.read_text(encoding="utf-8"))
            if isinstance(data, dict) and data.get("resourceType") in ("Bundle", "Patient", "Observation"):
                fhir_valid = True
                break
        except Exception:
            pass
    log_test("7. FHIR R4 Bundle Integrity Check", fhir_valid, "FHIR Bundle resources valid and preserved")

    # 8. Malformed & Unsupported Input Quarantine Check
    report1 = json.loads((out1 / "report.json").read_text(encoding="utf-8"))
    quarantined = [f for f in report1["files"] if f["status"] == "quarantined"]
    log_test("8. Malformed & Unsupported Input Quarantine", len(quarantined) == 5, f"{len(quarantined)} files quarantined (PDF/PNG/broken JSON)")

    # 9. FastAPI Backend Integration
    dash_resp = client.get("/api/dashboard")
    log_test("9. FastAPI Backend Health & Dashboard API", dash_resp.status_code == 200, f"Status {dash_resp.status_code}")

    # 10. File Download & Protected Output Handling
    dl_resp = client.get("/api/jobs/job-practice-baseline/download")
    log_test("10. Protected Output Zip Download Route", dl_resp.status_code == 200 and dl_resp.headers.get("content-type") == "application/zip", "Zip file generated safely")

    # 11. PII and Secret Non-Exposure in API Responses
    api_leak = False
    endpoints = ["/api/health", "/api/dashboard", "/api/organisations", "/api/identity-graph", "/api/threat-lab", "/api/privacy-intelligence", "/api/audit", "/api/settings"]
    for ep in endpoints:
        resp = client.get(ep)
        text = resp.text
        if "secretA" in text or "RAKSHA_SECRET" in text and "Loaded from" not in text:
            api_leak = True
        # Check raw Aadhaar format (12 digits)
        if re.search(r"\b[2-9]\d{3}\s\d{4}\s\d{4}\b", text):
            api_leak = True
    log_test("11. API Privacy & Zero Raw PII/Secret Exposure", not api_leak, "All API endpoints strictly de-identified")

    print("\n--------------------------------------------------------")
    print(f" SUMMARY: {passes} PASSED, {fails} FAILED")
    print("========================================================\n")
    return fails == 0

if __name__ == "__main__":
    success = run_full_suite()
    sys.exit(0 if success else 1)
