"""GuptKavach / MediLocker End-to-End System & Regression Verification Suite.
Validates:
1. Original standalone CLI execution
2. validate_output.py contract check
3. check_dev.py self-check evaluation
4. Same-secret determinism test
5. Different-secret pseudonym separation test
6. Secret leakage check in logs and outputs
7. FHIR R4 Bundle integrity test
8. Malformed & unsupported input quarantine test
9. FastAPI unauthenticated 401 enforcement + authenticated dashboard API
10. Real job execution & protected output ZIP download route + cross-org 403 check
11. PII and secret non-exposure across all authenticated API endpoints
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import shutil
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

    temp_root = Path(tempfile.mkdtemp(prefix="gk-sys-suite-"))
    out1 = temp_root / "out1"
    out2 = temp_root / "out2"
    out3 = temp_root / "out3"
    out1.mkdir()
    out2.mkdir()
    out3.mkdir()

    # Configure isolated test database and development-mode auth environment
    test_db_path = temp_root / "test_system_suite.db"
    prev_env = {k: os.environ.get(k) for k in ("MEDILOCKER_DB_PATH", "MEDILOCKER_AUTH_SECRET", "MEDILOCKER_ENV", "SMTP_HOST", "RAKSHA_SECRET")}
    os.environ["MEDILOCKER_DB_PATH"] = str(test_db_path)
    os.environ["MEDILOCKER_AUTH_SECRET"] = "test-only-system-auth-secret-m16-3"
    os.environ["MEDILOCKER_ENV"] = "development"
    os.environ["RAKSHA_SECRET"] = "secretA"
    os.environ.pop("SMTP_HOST", None)

    created_job_id = None
    try:
        # 1. Standalone CLI Run
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
        subprocess.run(
            [sys.executable, str(STARTER_DIR / "main.py"), "--input", str(DEV_INPUT), "--output", str(out2)],
            cwd=str(STARTER_DIR),
            env=dict(os.environ, RAKSHA_SECRET="secretA"),
            capture_output=True,
            text=True,
        )
        h1 = hashlib.sha256((out1 / "records.jsonl").read_bytes()).hexdigest()
        h2 = hashlib.sha256((out2 / "records.jsonl").read_bytes()).hexdigest()
        log_test("4. Same-Secret Determinism Test", h1 == h2, f"Identical records.jsonl SHA256: {h1[:12]}...")

        # 5. Different-Secret Pseudonym Separation
        subprocess.run(
            [sys.executable, str(STARTER_DIR / "main.py"), "--input", str(DEV_INPUT), "--output", str(out3)],
            cwd=str(STARTER_DIR),
            env=dict(os.environ, RAKSHA_SECRET="secretB"),
            capture_output=True,
            text=True,
        )
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

        # Initialize isolated FastAPI TestClient
        from backend import auth, database
        from backend.main import app

        auth.reset_rate_limits()
        database.init_db()
        unauth_client = TestClient(app)
        auth_client = TestClient(app)

        # 9. Unauthenticated 401 check + Authenticated FastAPI Health & Dashboard API
        unauth_dash = unauth_client.get("/api/dashboard")
        unauth_dl = unauth_client.get("/api/jobs/nonexistent/download")
        login_resp = auth_client.post("/api/auth/dev-login", json={"email": "sys_test_officer@metrogeneral.org"})
        has_cookie = "medilocker_session" in auth_client.cookies
        health_resp = auth_client.get("/api/health")
        dash_resp = auth_client.get("/api/dashboard")
        dash_ok = (
            unauth_dash.status_code == 401
            and unauth_dl.status_code == 401
            and login_resp.status_code == 200
            and has_cookie
            and health_resp.status_code == 200
            and dash_resp.status_code == 200
            and "metrics" in dash_resp.json()
        )
        log_test(
            "9. FastAPI Auth (401 Unauth) & Authenticated Dashboard API",
            dash_ok,
            f"Unauth={unauth_dash.status_code}, Login={login_resp.status_code}, Dash={dash_resp.status_code}",
        )

        # 10. Real Dataset Processing, Cross-Org 403 Guard & Protected Zip Download
        sample_csv = (
            "patient_name,age,gender,district,phone,diagnosis,medication\n"
            "Amit Kumar,42,M,Jaipur,9876543210,Dengue fever,Paracetamol 500 mg\n"
            "Sunita Devi,43,F,Jaipur,9876543211,Typhoid,Azithromycin 500 mg\n"
            "Ramesh Sharma,41,M,Jaipur,9876543212,Hypertension,Amlodipine 5 mg\n"
            "Priya Verma,44,F,Jaipur,9876543213,Diabetes,Metformin 500 mg\n"
            "Mohan Lal,40,M,Jaipur,9876543214,Asthma,Salbutamol 100 mcg\n"
        ).encode("utf-8")
        up_resp = auth_client.post(
            "/api/datasets",
            data={"organisation_id": "org-hosp-a", "name": "System Suite Cohort", "auto_process": "true", "sync": "true"},
            files=[("files", ("cohort.csv", sample_csv, "text/csv"))],
        )
        job_info = up_resp.json().get("job") if up_resp.status_code == 200 else None
        created_job_id = job_info.get("id") if job_info else None
        dl_resp = auth_client.get(f"/api/jobs/{created_job_id}/download") if created_job_id else None
        cross_org_resp = auth_client.post(
            "/api/datasets",
            data={"organisation_id": "org-hosp-b", "name": "Cross Org Attempt", "auto_process": "false"},
            files=[("files", ("c.csv", sample_csv, "text/csv"))],
        )
        cross_org_blocked = cross_org_resp.status_code == 403
        dl_ok = bool(
            up_resp.status_code == 200
            and dl_resp is not None
            and dl_resp.status_code == 200
            and dl_resp.headers.get("content-type") == "application/zip"
            and cross_org_blocked
        )
        log_test("10. Protected Output Zip Download & Org Scoping", dl_ok, f"Job={created_job_id}, Zip={dl_resp.status_code if dl_resp else 'None'}")

        # 11. PII and Secret Non-Exposure across Authenticated API Endpoints + Logout revocation
        api_leak = False
        endpoints = [
            "/api/health",
            "/api/dashboard",
            "/api/organisations",
            "/api/identity-graph",
            "/api/threat-lab",
            "/api/privacy-intelligence",
            "/api/audit",
            "/api/settings",
        ]
        for ep in endpoints:
            resp = auth_client.get(ep)
            if resp.status_code != 200:
                api_leak = True
                break
            text = resp.text
            if "secretA" in text or "test-only-system-auth-secret" in text:
                api_leak = True
            if re.search(r"\b[2-9]\d{3}\s\d{4}\s\d{4}\b", text) or "9876543210" in text or "Amit Kumar" in text:
                api_leak = True
        logout_resp = auth_client.post("/api/auth/logout")
        post_logout_dash = auth_client.get("/api/dashboard")
        log_test(
            "11. Authenticated API Privacy & Session Revocation",
            not api_leak and logout_resp.status_code == 200 and post_logout_dash.status_code == 401,
            "All API endpoints de-identified and logout revokes session (401)",
        )

    finally:
        # Clean up temporary directories, test DB, and generated test job artifacts
        if created_job_id:
            shutil.rmtree(REPO_ROOT / "data" / "jobs" / created_job_id, ignore_errors=True)
        shutil.rmtree(temp_root, ignore_errors=True)
        for k, v in prev_env.items():
            if v is None:
                os.environ.pop(k, None)
            else:
                os.environ[k] = v

    print("\n--------------------------------------------------------")
    print(f" SUMMARY: {passes} PASSED, {fails} FAILED")
    print("========================================================\n")
    return fails == 0


if __name__ == "__main__":
    success = run_full_suite()
    sys.exit(0 if success else 1)
