"""Comprehensive Milestone 17 Integration, Auth, RBAC, Pipeline & Dashboard Test Suite."""
from __future__ import annotations

import os
import re
import time
from pathlib import Path
from typing import Any, Dict, List
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

# Point DB to an isolated temporary SQLite file before importing backend
TEST_DB = Path(__file__).resolve().parent / "test_m17.db"


@pytest.fixture(autouse=True)
def isolated_env(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    db_file = tmp_path / "m17_test.db"
    monkeypatch.setenv("MEDILOCKER_DB_PATH", str(db_file))
    monkeypatch.setenv("MEDILOCKER_AUTH_SECRET", "test-auth-secret-key-m17")
    monkeypatch.setenv("RAKSHA_SECRET", "practice")
    monkeypatch.setenv("SMTP_HOST", "smtp.example.org")
    monkeypatch.setenv("SMTP_PORT", "587")
    monkeypatch.setenv("SMTP_FROM_EMAIL", "noreply@medilocker.local")
    monkeypatch.setenv("OTP_RESEND_COOLDOWN_SECONDS", "60")

    from backend import auth, database

    auth.reset_rate_limits()
    database.init_db()
    yield
    auth.reset_rate_limits()


@pytest.fixture
def client() -> TestClient:
    from backend.main import app

    return TestClient(app)


def _otp_login(client: TestClient, email: str, monkeypatch: pytest.MonkeyPatch) -> TestClient:
    sent_codes: List[str] = []

    def fake_send(to_email: str, otp_code: str, expiry_minutes: int = 5) -> None:
        sent_codes.append(otp_code)

    monkeypatch.setattr("backend.auth.send_otp_email", fake_send)
    r1 = client.post("/api/auth/otp/request", json={"email": email, "purpose": "login"})
    assert r1.status_code == 200
    assert len(sent_codes) == 1

    r2 = client.post(
        "/api/auth/otp/verify",
        json={"email": email, "code": sent_codes[0], "purpose": "login"},
    )
    assert r2.status_code == 200
    return client


# ==============================================================================
# 1. Dashboard & Empty State Tests
# ==============================================================================


def test_dashboard_requires_auth(client: TestClient):
    res = client.get("/api/dashboard/overview")
    assert res.status_code == 401


def test_empty_dashboard_states(client: TestClient, monkeypatch: pytest.MonkeyPatch):
    _otp_login(client, "admin@medilocker.local", monkeypatch)
    res = client.get("/api/dashboard/overview")
    assert res.status_code == 200
    body = res.json()

    m = body["metrics"]
    assert m["files_processed"]["value"] == 0
    assert m["files_processed"]["status"] == "NOT_RUN"
    assert m["records_processed"]["value"] == 0
    assert m["records_processed"]["status"] == "NOT_RUN"
    assert m["pii_detected"]["display"] == "Not measured"
    assert m["pii_detected"]["status"] == "NOT_MEASURED"
    assert m["clinical_preserved"]["display"] == "Not measured"
    assert m["clinical_preserved"]["status"] == "NOT_MEASURED"
    assert m["identity_precision"]["display"] == "Not measured"
    assert m["identity_precision"]["status"] == "NOT_MEASURED"
    assert m["canary_leaks"]["display"] == "Not tested"
    assert m["canary_leaks"]["status"] == "NOT_RUN"
    assert body["privacy_health"]["overall_readiness"] == "NOT_RUN"


# ==============================================================================
# 2. Full End-to-End Dataset -> Engine -> Assessments -> Passport -> Audit
# ==============================================================================


def test_full_pipeline_and_passport_verification(client: TestClient, monkeypatch: pytest.MonkeyPatch):
    _otp_login(client, "privacy@metrogeneral.org", monkeypatch)

    csv_content = (
        "patient_name,age,gender,phone,diagnosis,lab_result\n"
        "Rohan Sharma,44,M,9811223344,Type 2 Diabetes,HbA1c 7.2 mg/dL\n"
        "Sunita Devi,52,F,9822334455,Hypertension,BP 130/80 mmHg\n"
    ).encode("utf-8")

    res = client.post(
        "/api/datasets",
        data={"organisation_id": "org-hosp-a", "name": "Synthetic OPD Cohort", "auto_process": "true", "sync": "true"},
        files=[("files", ("opd_cohort.csv", csv_content, "text/csv"))],
    )
    assert res.status_code == 200
    payload = res.json()
    job = payload["job"]
    assert job is not None
    assert job["status"] in ("COMPLETED", "COMPLETED_WITH_WARNINGS")

    # Dashboard reflects real processed job
    dash = client.get("/api/dashboard/overview").json()
    assert dash["metrics"]["files_processed"]["value"] >= 1
    assert dash["metrics"]["records_processed"]["value"] >= 2
    assert dash["metrics"]["pii_detected"]["status"] == "PASS"
    assert dash["metrics"]["canary_leaks"]["status"] == "NOT_RUN"
    assert len(dash["recent_jobs"]) == 1

    # Job results & stages
    results = client.get(f"/api/jobs/{job['id']}/results").json()
    assert results["privacy_assessment"] is not None
    assert results["clinical_report"] is not None
    assert results["identity_cluster"] is not None
    assert results["passport"] is not None
    assert results["passport"]["signature_status"] == "UNSIGNED"

    # Passport verification & download
    passport_id = results["passport"]["id"]
    ver = client.post(f"/api/passports/{passport_id}/verify").json()
    assert ver["integrity_valid"] is True
    assert ver["signature_status"] == "UNSIGNED"

    dl_json = client.get(f"/api/passports/{passport_id}/download?format=json")
    assert dl_json.status_code == 200
    dl_html = client.get(f"/api/passports/{passport_id}/download?format=html")
    assert dl_html.status_code == 200
    assert "UNSIGNED" in dl_html.text

    # Audit events recorded
    audit = client.get("/api/audit/events").json()
    actions = {e["action"] for e in audit["events"]}
    assert "DATASET_UPLOADED" in actions
    assert "JOB_COMPLETED" in actions
    assert "PASSPORT_VERIFIED" in actions


def test_canary_pass_detection(client: TestClient, monkeypatch: pytest.MonkeyPatch):
    _otp_login(client, "privacy@metrogeneral.org", monkeypatch)
    csv_content = (
        "patient_name,phone,diagnosis,lab_result\n"
        "CANARY_FNAME_3311,9876543210,Diabetes,145 mg/dL\n"
    ).encode("utf-8")
    res = client.post(
        "/api/datasets",
        data={"organisation_id": "org-hosp-a", "name": "Canary Check", "auto_process": "true", "sync": "true"},
        files=[("files", ("note_canary.csv", csv_content, "text/csv"))],
    )
    assert res.status_code == 200
    dash = client.get("/api/dashboard/overview").json()
    assert dash["metrics"]["canary_leaks"]["status"] == "PASS"
    assert dash["metrics"]["canary_leaks"]["value"] == 0


def test_invalid_and_empty_uploads(client: TestClient, monkeypatch: pytest.MonkeyPatch):
    _otp_login(client, "privacy@metrogeneral.org", monkeypatch)

    bad_ext = client.post(
        "/api/datasets",
        data={"organisation_id": "org-hosp-a"},
        files=[("files", ("malware.exe", b"MZ", "application/octet-stream"))],
    )
    assert bad_ext.status_code == 400

    empty_file = client.post(
        "/api/datasets",
        data={"organisation_id": "org-hosp-a"},
        files=[("files", ("empty.csv", b"", "text/csv"))],
    )
    assert empty_file.status_code == 400


# ==============================================================================
# 3. Email OTP Security Tests
# ==============================================================================


def test_otp_security_controls(client: TestClient, monkeypatch: pytest.MonkeyPatch):
    sent: List[str] = []
    monkeypatch.setattr("backend.auth.send_otp_email", lambda to, code, expiry_minutes=5: sent.append(code))

    # Anti-enumeration: unknown email returns same generic 200 without sending
    r_unknown = client.post("/api/auth/otp/request", json={"email": "nobody@unknown.org"})
    assert r_unknown.status_code == 200
    assert r_unknown.json()["message"] == "If this account is eligible, a verification code will be sent."
    assert len(sent) == 0

    # Valid email sends OTP
    r_ok = client.post("/api/auth/otp/request", json={"email": "admin@medilocker.local"})
    assert r_ok.status_code == 200
    assert len(sent) == 1
    assert re.fullmatch(r"\d{6}", sent[0])

    # Resend cooldown enforced
    r_cool = client.post("/api/auth/otp/request", json={"email": "admin@medilocker.local"})
    assert r_cool.status_code == 429

    # Wrong OTP increments attempts and locks out after 5 tries
    for _ in range(5):
        r_bad = client.post(
            "/api/auth/otp/verify",
            json={"email": "admin@medilocker.local", "code": "000000"},
        )
        assert r_bad.status_code == 401

    # Even the real code is now rejected because max_attempts exceeded
    r_locked = client.post(
        "/api/auth/otp/verify",
        json={"email": "admin@medilocker.local", "code": sent[0]},
    )
    assert r_locked.status_code == 401


def test_otp_one_time_use_and_logout_revocation(client: TestClient, monkeypatch: pytest.MonkeyPatch):
    sent: List[str] = []
    monkeypatch.setattr("backend.auth.send_otp_email", lambda to, code, expiry_minutes=5: sent.append(code))
    client.post("/api/auth/otp/request", json={"email": "admin@medilocker.local"})
    code = sent[0]

    r1 = client.post("/api/auth/otp/verify", json={"email": "admin@medilocker.local", "code": code})
    assert r1.status_code == 200

    # Replay same OTP must fail
    r2 = client.post("/api/auth/otp/verify", json={"email": "admin@medilocker.local", "code": code})
    assert r2.status_code == 401

    # Authenticated /me works, then logout revokes session
    assert client.get("/api/auth/me").status_code == 200
    assert client.post("/api/auth/logout").status_code == 200
    assert client.get("/api/auth/me").status_code == 401


def test_smtp_failure_creates_no_session(client: TestClient, monkeypatch: pytest.MonkeyPatch):
    def fail_smtp(*args, **kwargs):
        raise RuntimeError("SMTP connection refused")

    monkeypatch.setattr("backend.auth.send_otp_email", fail_smtp)
    r = client.post("/api/auth/otp/request", json={"email": "admin@medilocker.local"})
    assert r.status_code == 502
    assert client.get("/api/auth/me").status_code == 401


# ==============================================================================
# 4. Google OAuth 2.0 / OIDC Tests
# ==============================================================================


def test_google_disabled_returns_503(client: TestClient, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.delenv("GOOGLE_CLIENT_ID", raising=False)
    monkeypatch.delenv("GOOGLE_CLIENT_SECRET", raising=False)
    cfg = client.get("/api/auth/config").json()
    assert cfg["google_enabled"] is False
    assert client.get("/api/auth/google/login").status_code == 503


def test_google_oauth_flow_and_security_checks(client: TestClient, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("GOOGLE_CLIENT_ID", "test-client-id.apps.googleusercontent.com")
    monkeypatch.setenv("GOOGLE_CLIENT_SECRET", "test-client-secret")
    monkeypatch.setenv("GOOGLE_REDIRECT_URI", "http://localhost:3001/auth/google/callback")

    login_res = client.get("/api/auth/google/login")
    assert login_res.status_code == 200
    state = login_res.json()["state"]

    # Retrieve stored nonce from DB for mock ID token
    from backend.database import get_db

    with get_db() as conn:
        nonce = conn.execute("SELECT nonce FROM oauth_states WHERE state = ?", (state,)).fetchone()["nonce"]

    # Invalid state rejected
    bad_state = client.post("/api/auth/google/callback", json={"code": "abc", "state": "wrong-state"})
    assert bad_state.status_code == 400

    class MockResp:
        status_code = 200
        def json(self):
            return {"id_token": "mock.jwt.token"}

    monkeypatch.setattr("backend.auth.http_requests.post", lambda *a, **kw: MockResp())

    # Mock verify_oauth2_token returning valid Google user
    monkeypatch.setattr(
        "backend.auth.google_id_token.verify_oauth2_token",
        lambda tok, req, cid: {
            "iss": "https://accounts.google.com",
            "aud": cid,
            "sub": "google-sub-12345",
            "email": "newdoctor@hospital.org",
            "email_verified": True,
            "name": "Dr. New Doctor",
            "nonce": nonce,
        },
    )
    ok = client.post("/api/auth/google/callback", json={"code": "auth-code", "state": state})
    assert ok.status_code == 200
    assert ok.json()["user"]["email"] == "newdoctor@hospital.org"


def test_google_blocks_unlinked_existing_email_takeover(client: TestClient, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("GOOGLE_CLIENT_ID", "test-client-id.apps.googleusercontent.com")
    monkeypatch.setenv("GOOGLE_CLIENT_SECRET", "test-client-secret")
    monkeypatch.setenv("GOOGLE_REDIRECT_URI", "http://localhost:3001/auth/google/callback")

    state = client.get("/api/auth/google/login").json()["state"]
    from backend.database import get_db

    with get_db() as conn:
        nonce = conn.execute("SELECT nonce FROM oauth_states WHERE state = ?", (state,)).fetchone()["nonce"]

    class MockResp:
        status_code = 200
        def json(self):
            return {"id_token": "mock.jwt.token"}

    monkeypatch.setattr("backend.auth.http_requests.post", lambda *a, **kw: MockResp())
    monkeypatch.setattr(
        "backend.auth.google_id_token.verify_oauth2_token",
        lambda tok, req, cid: {
            "iss": "https://accounts.google.com",
            "aud": cid,
            "sub": "attacker-sub-999",
            "email": "privacy@metrogeneral.org",  # already exists via Email OTP
            "email_verified": True,
            "nonce": nonce,
        },
    )
    blocked = client.post("/api/auth/google/callback", json={"code": "auth-code", "state": state})
    assert blocked.status_code == 409


# ==============================================================================
# 5. RBAC & Organisation Isolation Tests
# ==============================================================================


def test_rbac_and_cross_org_isolation(client: TestClient, monkeypatch: pytest.MonkeyPatch):
    # Sign in as Researcher (belongs only to org-res-d)
    _otp_login(client, "research@nie.org", monkeypatch)

    # Researcher cannot upload datasets to org-hosp-a (cross-org & role check)
    up = client.post(
        "/api/datasets",
        data={"organisation_id": "org-hosp-a"},
        files=[("files", ("test.csv", b"a,b\n1,2\n", "text/csv"))],
    )
    assert up.status_code == 403

    # Researcher cannot create new organisations (PLATFORM_ADMIN only)
    org_create = client.post("/api/organisations", json={"name": "Rogue Org", "org_type": "Lab"})
    assert org_create.status_code == 403

    # Researcher cannot approve research requests
    req_create = client.post(
        "/api/research/requests",
        json={"title": "Cohort Study", "institution": "NIE", "purpose": "Stats"},
    )
    assert req_create.status_code == 200
    req_id = req_create.json()["id"]

    approve = client.post(f"/api/research/requests/{req_id}/approve")
    assert approve.status_code == 403

    # Auditor cannot modify settings
    client.post("/api/auth/logout")
    _otp_login(client, "audit@medilocker.local", monkeypatch)
    upd = client.post("/api/settings", json={"quarantine_threshold": 0.9})
    assert upd.status_code == 403
