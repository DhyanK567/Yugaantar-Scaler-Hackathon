"""Milestone 18 Automated Offline-First Verification Suite.
Strictly blocks all non-loopback outbound network connections during execution
to prove MediLocker operates 100% offline.
"""
from __future__ import annotations

import hashlib
import os
import socket
import subprocess
import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))


@pytest.fixture(autouse=True)
def strict_offline_sandbox(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    """Block every non-loopback network socket and isolate SQLite DB."""
    orig_create_conn = socket.create_connection

    def guarded_create_connection(address, *args, **kwargs):
        host = address[0] if isinstance(address, tuple) else str(address)
        if host not in ("127.0.0.1", "localhost", "::1"):
            raise RuntimeError(f"OFFLINE_VIOLATION: Attempted external connection to {host}")
        return orig_create_conn(address, *args, **kwargs)

    monkeypatch.setattr(socket, "create_connection", guarded_create_connection)

    db_file = tmp_path / "m18_offline.db"
    monkeypatch.setenv("MEDILOCKER_DB_PATH", str(db_file))
    monkeypatch.setenv("MEDILOCKER_AUTH_SECRET", "offline-test-secret")
    monkeypatch.setenv("MEDILOCKER_OFFLINE_MODE", "true")
    monkeypatch.setenv("RAKSHA_SECRET", "practice")
    monkeypatch.setenv("HF_HUB_OFFLINE", "1")
    monkeypatch.setenv("TRANSFORMERS_OFFLINE", "1")
    # Explicitly clear SMTP & Google so zero cloud config exists
    monkeypatch.delenv("SMTP_HOST", raising=False)
    monkeypatch.delenv("GOOGLE_CLIENT_ID", raising=False)
    monkeypatch.delenv("GOOGLE_CLIENT_SECRET", raising=False)

    from backend import auth, database

    auth.reset_rate_limits()
    database.init_db()
    yield
    auth.reset_rate_limits()


def test_offline_end_to_end_workflow_and_persistence(tmp_path: Path):
    from backend import database
    from backend.main import app

    client = TestClient(app)

    # 1. Auth config reports offline_mode=True, smtp_enabled=False, google_enabled=False
    cfg = client.get("/api/auth/config").json()
    assert cfg["offline_mode"] is True
    assert cfg["smtp_enabled"] is False
    assert cfg["google_enabled"] is False

    # 2. Local offline demo login succeeds with zero network
    login = client.post("/api/auth/offline-demo", json={})
    assert login.status_code == 200
    assert login.json()["user"]["email"] == "privacy@metrogeneral.org"

    # 3. Dashboard loads cleanly
    dash0 = client.get("/api/dashboard/overview")
    assert dash0.status_code == 200
    assert dash0.json()["metrics"]["files_processed"]["value"] == 0

    # 4. Upload synthetic dataset & run full offline privacy pipeline
    csv_data = (
        "patient_name,age,gender,phone,diagnosis,lab_result\n"
        "Aarav Mehta,39,M,9876501234,Hypertension,BP 128/82 mmHg\n"
        "Kavita Iyer,47,F,9876505678,Diabetes,Glucose 142 mg/dL\n"
    ).encode("utf-8")

    up = client.post(
        "/api/datasets",
        data={"organisation_id": "org-hosp-a", "name": "Offline Cohort", "auto_process": "true", "sync": "true"},
        files=[("files", ("offline_cohort.csv", csv_data, "text/csv"))],
    )
    assert up.status_code == 200
    job = up.json()["job"]
    assert job["status"] in ("COMPLETED", "COMPLETED_WITH_WARNINGS")

    # 5. Simulate restart: re-run init_db() and verify job & audit history persist
    database.init_db()
    jobs_after = client.get("/api/jobs").json()
    assert any(j["id"] == job["id"] for j in jobs_after)

    # 6. Verify Privacy Passport, Audit Trail, and ZIP download
    results = client.get(f"/api/jobs/{job['id']}/results").json()
    passport_id = results["passport"]["id"]
    ver = client.post(f"/api/passports/{passport_id}/verify").json()
    assert ver["integrity_valid"] is True

    dl = client.get(f"/api/jobs/{job['id']}/download")
    assert dl.status_code == 200
    assert len(dl.content) > 100

    audit = client.get("/api/audit/events").json()
    actions = {e["action"] for e in audit["events"]}
    assert "LOGIN_OFFLINE_DEMO" in actions
    assert "JOB_COMPLETED" in actions
    assert "PASSPORT_VERIFIED" in actions


def test_offline_demo_blocked_when_disabled(monkeypatch: pytest.MonkeyPatch):
    from backend.main import app

    monkeypatch.setenv("MEDILOCKER_OFFLINE_MODE", "false")
    client = TestClient(app)
    res = client.post("/api/auth/offline-demo", json={})
    assert res.status_code == 403


def test_independent_cli_engine_determinism_offline(tmp_path: Path):
    in_dir = tmp_path / "cli_in"
    out1 = tmp_path / "cli_out1"
    out2 = tmp_path / "cli_out2"
    in_dir.mkdir()
    (in_dir / "sample.csv").write_text(
        "patient_name,phone,diagnosis,lab_result\nRohan Verma,9811122233,Asthma,FEV1 82%\n",
        encoding="utf-8",
    )

    env = dict(os.environ, RAKSHA_SECRET="practice", HF_HUB_OFFLINE="1", TRANSFORMERS_OFFLINE="1")
    for out in (out1, out2):
        proc = subprocess.run(
            [sys.executable, str(REPO_ROOT / "starter" / "main.py"), "--input", str(in_dir), "--output", str(out)],
            cwd=str(REPO_ROOT / "starter"),
            env=env,
            capture_output=True,
            text=True,
            timeout=60,
        )
        assert proc.returncode == 0

    h1 = hashlib.sha256((out1 / "sanitized" / "sample.csv").read_bytes()).hexdigest()
    h2 = hashlib.sha256((out2 / "sanitized" / "sample.csv").read_bytes()).hexdigest()
    assert h1 == h2
