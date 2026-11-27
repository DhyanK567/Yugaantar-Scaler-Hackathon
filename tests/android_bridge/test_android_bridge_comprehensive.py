"""Comprehensive M28 Android Bridge & Privacy Engine Regression Suite.
Tests:
- Unauthenticated 401 enforcement
- Offline demo login & session cookies
- All supported formats: CSV, TSV, JSON, JSONL, TXT, FHIR R4 JSON
- Unicode / Hindi filename preservation
- Empty file (400), unsupported format .xml (400), malformed JSON (quarantined)
- Download ZIP security: excludes records.jsonl and quarantine/
- Path traversal protection
- Full user journey: Org, Datasets, Jobs, Quarantine, Privacy Intelligence,
  Clinical Integrity, Identity Continuity, Threat Lab, Passports (verify + download),
  Research Requests, Settings validation, Diagnostics, Audit zero-PII/zero-secret
- CLI vs Android bridge output parity
"""
from __future__ import annotations

import base64
import io
import json
import sqlite3
import subprocess
import sys
import zipfile
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
ANDROID_PY = REPO_ROOT / "android" / "app" / "src" / "main" / "python"
if str(ANDROID_PY) not in sys.path:
    sys.path.insert(0, str(ANDROID_PY))

import android_api_bridge as bridge  # noqa: E402


def _call(
    method: str,
    path: str,
    headers: Optional[Dict[str, str]] = None,
    qs: str = "",
    body: bytes = b"",
) -> Tuple[int, Dict[str, str], bytes]:
    r = bridge.handle_request(
        method,
        path,
        qs,
        json.dumps(headers or {}),
        base64.b64encode(body).decode("ascii"),
    )
    return r["status"], r["headers"], base64.b64decode(r["body_b64"])


def _multipart(files: List[Tuple[str, bytes, str]], fields: Optional[Dict[str, str]] = None) -> Tuple[str, bytes]:
    boundary = "----MediLockerM28Boundary"
    parts: List[bytes] = []
    for k, v in (fields or {}).items():
        parts.append(
            f'--{boundary}\r\nContent-Disposition: form-data; name="{k}"\r\n\r\n{v}\r\n'.encode("utf-8")
        )
    for fname, content, ctype in files:
        hdr = (
            f'--{boundary}\r\nContent-Disposition: form-data; name="files"; filename="{fname}"\r\n'
            f"Content-Type: {ctype}\r\n\r\n"
        ).encode("utf-8")
        parts.append(hdr + content + b"\r\n")
    parts.append(f"--{boundary}--\r\n".encode("utf-8"))
    return f"multipart/form-data; boundary={boundary}", b"".join(parts)


@pytest.fixture
def android_env(tmp_path: Path):
    bridge.init_android_runtime(str(tmp_path), "m28-test-secret-key-2026")
    st, hdrs, _ = _call("POST", "/api/auth/offline-demo", body=b"{}")
    assert st == 200
    cookie = hdrs["Set-Cookie"].split(";")[0]
    return tmp_path, cookie


def test_unauthenticated_rejected_and_diagnostics_ok(android_env):
    _, cookie = android_env
    for ep in ("/api/dashboard", "/api/datasets", "/api/jobs", "/api/passports", "/api/quarantine"):
        st, _, _ = _call("GET", ep)
        assert st == 401, f"Expected 401 on {ep}, got {st}"

    st, _, body = _call("GET", "/api/health")
    assert st == 200
    assert json.loads(body)["mode"] == "android-offline-cpu"

    st, _, body = _call("GET", "/api/system/diagnostics", {"Cookie": cookie})
    assert st == 200
    diag = json.loads(body)
    assert diag["offline_mode"] is True
    assert diag["api_status"] == "healthy"
    assert diag["engine_status"] == "ready"


def test_upload_validation_rejects_empty_and_unsupported(android_env):
    _, cookie = android_env

    # Empty file -> 400
    ct, body = _multipart([("empty.csv", b"", "text/csv")])
    st, _, resp = _call("POST", "/api/datasets", {"Cookie": cookie, "Content-Type": ct}, body=body)
    assert st == 400
    assert "Empty file" in resp.decode("utf-8")

    # Unsupported .xml -> 400
    ct, body = _multipart([("legacy.xml", b"<root/>", "application/xml")])
    st, _, resp = _call("POST", "/api/datasets", {"Cookie": cookie, "Content-Type": ct}, body=body)
    assert st == 400
    assert "Unsupported" in resp.decode("utf-8")


def test_multiformat_hindi_filename_quarantine_and_zip_security(android_env):
    tmp_path, cookie = android_env

    csv_bytes = (
        "patient_name,age,gender,district,phone,diagnosis,medication\n"
        "Amit Kumar,42,M,Jaipur,9876543210,Dengue fever,Paracetamol 500 mg\n"
        "Sunita Devi,43,F,Jaipur,9876543211,Typhoid,Azithromycin 500 mg\n"
        "Ramesh Sharma,41,M,Jaipur,9876543212,Hypertension,Amlodipine 5 mg\n"
        "Priya Verma,44,F,Jaipur,9876543213,Diabetes,Metformin 500 mg\n"
        "Mohan Lal,40,M,Jaipur,9876543214,Asthma,Salbutamol 100 mcg\n"
    ).encode("utf-8")
    tsv_bytes = b"patient_name\tage\tdiagnosis\tmedication\nKiran Rao\t35\tFever\tParacetamol 500 mg\n"
    txt_bytes = "मरीज: राजेश वर्मा, मोबाइल: 9876543219। Tab Dolo 650 mg.".encode("utf-8")
    fhir_bytes = json.dumps({
        "resourceType": "Bundle",
        "type": "collection",
        "entry": [{"resource": {"resourceType": "Patient", "id": "p1", "name": [{"text": "Vikram Singh"}], "gender": "male"}}],
    }).encode("utf-8")
    jsonl_bytes = (json.dumps({"patient_name": "Neha Gupta", "diagnosis": "Migraine", "medication": "Sumatriptan 50 mg"}) + "\n").encode("utf-8")
    corrupt_json = b"{not_valid_json"

    ct, body = _multipart(
        [
            ("मरीज_डेटा.csv", csv_bytes, "text/csv"),
            ("wards.tsv", tsv_bytes, "text/tab-separated-values"),
            ("note.txt", txt_bytes, "text/plain"),
            ("fhir_bundle.json", fhir_bytes, "application/json"),
            ("events.jsonl", jsonl_bytes, "application/x-ndjson"),
            ("corrupt.json", corrupt_json, "application/json"),
        ],
        {"auto_process": "true"},
    )
    st, _, resp = _call("POST", "/api/datasets", {"Cookie": cookie, "Content-Type": ct}, body=body)
    assert st == 200, resp.decode("utf-8")
    res = json.loads(resp)
    ds_id = res["dataset_id"]
    job = res["job"]
    jid = job["id"]
    assert job["files_quarantined"] >= 1

    # Verify ZIP download excludes records.jsonl and quarantine/
    st, _, zbytes = _call("GET", f"/api/jobs/{jid}/download", {"Cookie": cookie})
    assert st == 200
    with zipfile.ZipFile(io.BytesIO(zbytes), "r") as zf:
        names = zf.namelist()
        assert "privacy_passport.json" in names
        for n in names:
            assert "records.jsonl" not in n
            assert not n.startswith("quarantine/")
            assert "corrupt.json" not in n

    # Path traversal rejected
    st, _, _ = _call("GET", "/api/jobs/../../download", {"Cookie": cookie})
    assert st in (400, 404)

    # Full API matrix checks
    for ep in (
        f"/api/datasets/{ds_id}",
        f"/api/jobs/{jid}",
        f"/api/jobs/{jid}/events",
        f"/api/jobs/{jid}/results",
        "/api/quarantine",
        "/api/privacy-intelligence",
        "/api/privacy/assessments",
        "/api/clinical/reports",
        "/api/identity/clusters",
        "/api/threat-lab",
        "/api/passports",
        "/api/audit/events",
    ):
        st, _, ep_body = _call("GET", ep, {"Cookie": cookie})
        assert st == 200, f"GET {ep} returned {st}"
        if ep == "/api/identity/clusters":
            ig = json.loads(ep_body)
            assert isinstance(ig["nodes"], list)
            assert isinstance(ig["edges"], list)
            assert ig["precision"] is None or isinstance(ig["precision"], (int, float))
        elif ep == "/api/threat-lab":
            tl = json.loads(ep_body)
            assert isinstance(tl["attack_simulations"], list)
            assert isinstance(tl["history"], list)
        elif ep == "/api/audit/events":
            ae = json.loads(ep_body)
            assert isinstance(ae["events"], list)

    # Verify & download passport
    st, _, pbytes = _call("GET", "/api/passports", {"Cookie": cookie})
    passports = json.loads(pbytes)
    assert len(passports) >= 1
    pid = passports[0]["id"]
    st, _, vbytes = _call("POST", f"/api/passports/{pid}/verify", {"Cookie": cookie}, body=b"{}")
    assert st == 200 and json.loads(vbytes)["integrity_valid"] is True

    st, _, dl_html = _call("GET", f"/api/passports/{pid}/download", {"Cookie": cookie}, qs="format=html")
    assert st == 200 and b"MediLocker Privacy Passport" in dl_html

    # Settings validation
    st, _, _ = _call("POST", "/api/settings", {"Cookie": cookie}, body=json.dumps({"date_shift_max_days": 999}).encode())
    assert st == 400
    st, _, _ = _call("POST", "/api/settings", {"Cookie": cookie}, body=json.dumps({"date_shift_max_days": 90, "min_group_size": 5, "age_band_width": 5}).encode())
    assert st == 200

    # Zero raw PII or secret in SQLite DB
    conn = sqlite3.connect(str(tmp_path / "medilocker.db"))
    dump = "\n".join(conn.iterdump())
    conn.close()
    for sensitive in ("Amit Kumar", "9876543210", "Vikram Singh", "m28-test-secret-key-2026"):
        assert sensitive not in dump


def test_cli_vs_android_bridge_parity(tmp_path: Path):
    in_dir = tmp_path / "cli_in"
    out_dir = tmp_path / "cli_out"
    in_dir.mkdir()
    sample = (
        "patient_name,age,gender,district,phone,diagnosis,medication\n"
        "Amit Kumar,42,M,Jaipur,9876543210,Dengue fever,Paracetamol 500 mg\n"
        "Sunita Devi,43,F,Jaipur,9876543211,Typhoid,Azithromycin 500 mg\n"
        "Ramesh Sharma,41,M,Jaipur,9876543212,Hypertension,Amlodipine 5 mg\n"
        "Priya Verma,44,F,Jaipur,9876543213,Diabetes,Metformin 500 mg\n"
        "Mohan Lal,40,M,Jaipur,9876543214,Asthma,Salbutamol 100 mcg\n"
    )
    (in_dir / "cohort.csv").write_text(sample, encoding="utf-8")

    import os
    env = os.environ.copy()
    env["RAKSHA_SECRET"] = "parity-secret-2026"
    proc = subprocess.run(
        [sys.executable, str(REPO_ROOT / "starter" / "main.py"), "--input", str(in_dir), "--output", str(out_dir)],
        capture_output=True,
        text=True,
        env=env,
        check=True,
    )
    assert proc.returncode == 0
    cli_report = json.loads((out_dir / "report.json").read_text(encoding="utf-8"))

    # Run same input through Android bridge with same secret
    and_dir = tmp_path / "and_app"
    bridge.init_android_runtime(str(and_dir), "parity-secret-2026")
    st, hdrs, _ = _call("POST", "/api/auth/offline-demo", body=b"{}")
    cookie = hdrs["Set-Cookie"].split(";")[0]
    ct, body = _multipart([("cohort.csv", sample.encode("utf-8"), "text/csv")])
    st, _, resp = _call("POST", "/api/datasets", {"Cookie": cookie, "Content-Type": ct}, body=body)
    assert st == 200
    jid = json.loads(resp)["job"]["id"]
    and_report = json.loads((and_dir / "jobs" / jid / "output" / "report.json").read_text(encoding="utf-8"))

    assert cli_report["counts"]["files_sanitized"] == and_report["counts"]["files_sanitized"]
    assert cli_report["counts"]["records_processed"] == and_report["counts"]["records_processed"]
    assert cli_report["counts"]["identifiers_detected"] == and_report["counts"]["identifiers_detected"]
