"""In-Process Android API Bridge for MediLocker (Chaquopy CPython).
Serves all /api/* routes locally on Android using SQLite in private app storage
and invokes the real GuptKavach / MediLocker privacy engine (starter/main.py)
in-process without subprocesses or external network calls.
"""
from __future__ import annotations

import base64
import hashlib
import hmac
import io
import json
import os
import re
import secrets
import shutil
import sqlite3
import sys
import time
import zipfile
from email.parser import BytesParser
from email.policy import default as email_default_policy
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
from urllib.parse import parse_qs

# Ensure starter/ modules are on sys.path
_HERE = Path(__file__).resolve().parent
if str(_HERE) not in sys.path:
    sys.path.insert(0, str(_HERE))

import main as engine_main  # starter/main.py
from verify_passport import verify_passport_bundle
from raksha_engine.clinical_validator import analyze_clinical_drift
from raksha_engine.attacker import RecordProfile, simulate_attacks

_APP_DIR: Path = Path(".")
_DB_PATH: Path = Path("medilocker.db")
_RAKSHA_SECRET: str = ""


def init_android_runtime(files_dir: str, raksha_secret: str) -> None:
    global _APP_DIR, _DB_PATH, _RAKSHA_SECRET
    _APP_DIR = Path(files_dir).resolve()
    _APP_DIR.mkdir(parents=True, exist_ok=True)
    (_APP_DIR / "datasets").mkdir(parents=True, exist_ok=True)
    (_APP_DIR / "jobs").mkdir(parents=True, exist_ok=True)
    _DB_PATH = _APP_DIR / "medilocker.db"
    _RAKSHA_SECRET = raksha_secret
    os.environ["RAKSHA_SECRET"] = raksha_secret
    os.environ["MEDILOCKER_OFFLINE_MODE"] = "true"
    engine_main.SECRET = raksha_secret.encode("utf-8")
    _init_db()


def _get_db() -> sqlite3.Connection:
    conn = sqlite3.connect(str(_DB_PATH))
    conn.row_factory = sqlite3.Row
    return conn


def _init_db() -> None:
    with _get_db() as conn:
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS organisations (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                org_type TEXT NOT NULL,
                region TEXT,
                status TEXT DEFAULT 'ACTIVE',
                records_contributed INTEGER DEFAULT 0,
                joined_at REAL
            );
            CREATE TABLE IF NOT EXISTS users (
                id TEXT PRIMARY KEY,
                email TEXT UNIQUE NOT NULL,
                full_name TEXT,
                status TEXT DEFAULT 'ACTIVE',
                platform_role TEXT DEFAULT 'USER',
                created_at REAL
            );
            CREATE TABLE IF NOT EXISTS memberships (
                id TEXT PRIMARY KEY,
                user_id TEXT NOT NULL,
                organisation_id TEXT NOT NULL,
                role TEXT NOT NULL,
                created_at REAL
            );
            CREATE TABLE IF NOT EXISTS sessions (
                id TEXT PRIMARY KEY,
                user_id TEXT NOT NULL,
                token_hash TEXT UNIQUE NOT NULL,
                active_org_id TEXT,
                created_at REAL,
                expires_at REAL,
                revoked_at REAL
            );
            CREATE TABLE IF NOT EXISTS datasets (
                id TEXT PRIMARY KEY,
                organisation_id TEXT NOT NULL,
                name TEXT NOT NULL,
                status TEXT NOT NULL,
                files_count INTEGER DEFAULT 0,
                total_bytes INTEGER DEFAULT 0,
                storage_path TEXT,
                manifest_sha256 TEXT,
                created_by TEXT,
                created_at REAL
            );
            CREATE TABLE IF NOT EXISTS jobs (
                id TEXT PRIMARY KEY,
                dataset_id TEXT,
                organisation_id TEXT NOT NULL,
                input_name TEXT,
                status TEXT NOT NULL,
                current_stage TEXT,
                release_decision TEXT DEFAULT 'NOT_EVALUATED',
                files_total INTEGER DEFAULT 0,
                files_sanitized INTEGER DEFAULT 0,
                files_quarantined INTEGER DEFAULT 0,
                records_processed INTEGER DEFAULT 0,
                records_linked INTEGER DEFAULT 0,
                identifiers_detected INTEGER DEFAULT 0,
                duration_secs REAL DEFAULT 0.0,
                created_at REAL,
                completed_at REAL
            );
            CREATE TABLE IF NOT EXISTS privacy_assessments (
                id TEXT PRIMARY KEY,
                job_id TEXT UNIQUE NOT NULL,
                dataset_id TEXT,
                organisation_id TEXT,
                pii_detected INTEGER DEFAULT 0,
                residual_leakage INTEGER DEFAULT 0,
                canary_planted INTEGER DEFAULT 0,
                canary_leaks INTEGER DEFAULT 0,
                canary_status TEXT DEFAULT 'NOT_RUN',
                qi_risk_score REAL DEFAULT 0.0,
                reid_risk_level TEXT DEFAULT 'NOT_MEASURED',
                release_eligible INTEGER DEFAULT 0,
                details_json TEXT,
                created_at REAL
            );
            CREATE TABLE IF NOT EXISTS clinical_reports (
                id TEXT PRIMARY KEY,
                job_id TEXT UNIQUE NOT NULL,
                organisation_id TEXT,
                expected_values INTEGER DEFAULT 0,
                preserved_values INTEGER DEFAULT 0,
                modified_values INTEGER DEFAULT 0,
                missing_values INTEGER DEFAULT 0,
                medication_integrity REAL,
                dosage_integrity REAL,
                lab_integrity REAL,
                vital_integrity REAL,
                fhir_integrity TEXT DEFAULT 'NOT_MEASURED',
                details_json TEXT,
                created_at REAL
            );
            CREATE TABLE IF NOT EXISTS identity_clusters (
                id TEXT PRIMARY KEY,
                job_id TEXT UNIQUE NOT NULL,
                organisation_id TEXT,
                precision REAL,
                recall REAL,
                f05 REAL,
                false_merges INTEGER DEFAULT 0,
                total_patients INTEGER DEFAULT 0,
                cross_hospital_links INTEGER DEFAULT 0,
                abstentions INTEGER DEFAULT 0,
                conflicts INTEGER DEFAULT 0,
                graph_json TEXT,
                created_at REAL
            );
            CREATE TABLE IF NOT EXISTS attack_runs (
                id TEXT PRIMARY KEY,
                job_id TEXT,
                dataset_id TEXT,
                organisation_id TEXT,
                profile TEXT,
                risk_score REAL DEFAULT 0.0,
                blocked_count INTEGER DEFAULT 0,
                total_count INTEGER DEFAULT 0,
                results_json TEXT,
                created_at REAL
            );
            CREATE TABLE IF NOT EXISTS passports (
                id TEXT PRIMARY KEY,
                job_id TEXT UNIQUE NOT NULL,
                dataset_id TEXT,
                organisation_id TEXT,
                manifest_hash TEXT,
                signature_status TEXT DEFAULT 'UNSIGNED',
                passport_json TEXT,
                verified_at REAL,
                created_at REAL
            );
            CREATE TABLE IF NOT EXISTS research_requests (
                id TEXT PRIMARY KEY,
                title TEXT NOT NULL,
                requestor_org TEXT NOT NULL,
                target_orgs TEXT,
                dataset_id TEXT,
                purpose TEXT,
                status TEXT DEFAULT 'PENDING',
                created_at REAL
            );
            CREATE TABLE IF NOT EXISTS audit_events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp REAL NOT NULL,
                actor_id TEXT,
                actor_email TEXT,
                actor_role TEXT,
                organisation_id TEXT,
                action TEXT NOT NULL,
                resource_type TEXT NOT NULL,
                resource_id TEXT,
                outcome TEXT NOT NULL,
                details TEXT
            );
            """
        )
        cnt = conn.execute("SELECT COUNT(*) FROM organisations").fetchone()[0]
        if cnt == 0:
            now = time.time()
            conn.executemany(
                "INSERT INTO organisations (id, name, org_type, region, status, records_contributed, joined_at) VALUES (?, ?, ?, ?, 'ACTIVE', 0, ?)",
                [
                    ("org-hosp-a", "Metro General Hospital", "Hospital", "Delhi NCR", now),
                    ("org-hosp-b", "Apex Care Medical Centre", "Hospital", "Mumbai", now),
                    ("org-lab-c", "ThyroCare Bio Diagnostics", "Diagnostic Lab", "Bengaluru", now),
                ],
            )


def _audit(action: str, resource_type: str, resource_id: Optional[str], outcome: str, details: str, user: Optional[Dict[str, Any]] = None, org_id: Optional[str] = None) -> None:
    safe_details = re.sub(r"\b[2-9]\d{3}\s\d{4}\s\d{4}\b", "[REDACTED_ID]", details or "")
    safe_details = re.sub(r"(?:\+91[\s-]?)?[6-9]\d{9}\b", "[REDACTED_PHONE]", safe_details)
    with _get_db() as conn:
        conn.execute(
            "INSERT INTO audit_events (timestamp, actor_id, actor_email, actor_role, organisation_id, action, resource_type, resource_id, outcome, details) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                time.time(),
                user["id"] if user else "system",
                user["email"] if user else "android-local@medilocker.local",
                user.get("active_role") if user else "SYSTEM",
                org_id or (user.get("active_org_id") if user else None),
                action,
                resource_type,
                resource_id,
                outcome,
                safe_details,
            ),
        )


def _hash_token(raw: str) -> str:
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def _create_offline_session(email: str) -> Tuple[str, Dict[str, Any]]:
    norm = (email or "privacy@metrogeneral.org").strip().lower()
    now = time.time()
    with _get_db() as conn:
        u = conn.execute("SELECT * FROM users WHERE lower(email) = ?", (norm,)).fetchone()
        if not u:
            uid = f"usr-{secrets.token_hex(6)}"
            conn.execute("INSERT INTO users (id, email, full_name, status, platform_role, created_at) VALUES (?, ?, ?, 'ACTIVE', 'PLATFORM_ADMIN', ?)", (uid, norm, norm.split("@")[0], now))
            conn.execute("INSERT INTO memberships (id, user_id, organisation_id, role, created_at) VALUES (?, ?, 'org-hosp-a', 'PRIVACY_OFFICER', ?)", (f"mem-{secrets.token_hex(6)}", uid, now))
        else:
            uid = u["id"]

        raw_tok = secrets.token_urlsafe(32)
        conn.execute(
            "INSERT INTO sessions (id, user_id, token_hash, active_org_id, created_at, expires_at) VALUES (?, ?, ?, 'org-hosp-a', ?, ?)",
            (f"ses-{secrets.token_hex(6)}", uid, _hash_token(raw_tok), now, now + 86400),
        )
    ctx = _load_user_from_token(raw_tok)
    return raw_tok, ctx  # type: ignore


def _load_user_from_token(raw_tok: Optional[str]) -> Optional[Dict[str, Any]]:
    if not raw_tok:
        return None
    with _get_db() as conn:
        s = conn.execute(
            "SELECT * FROM sessions WHERE token_hash = ? AND revoked_at IS NULL AND expires_at > ?",
            (_hash_token(raw_tok), time.time()),
        ).fetchone()
        if not s:
            return None
        u = conn.execute("SELECT * FROM users WHERE id = ?", (s["user_id"],)).fetchone()
        if not u:
            return None
        mems = [
            dict(r)
            for r in conn.execute(
                "SELECT m.id, m.organisation_id, m.role, o.name as organisation_name, o.org_type FROM memberships m JOIN organisations o ON o.id = m.organisation_id WHERE m.user_id = ?",
                (u["id"],),
            ).fetchall()
        ]
        active_org = s["active_org_id"] or (mems[0]["organisation_id"] if mems else "org-hosp-a")
        return {
            "id": u["id"],
            "email": u["email"],
            "full_name": u["full_name"],
            "platform_role": u["platform_role"],
            "active_org_id": active_org,
            "active_role": "PRIVACY_OFFICER",
            "memberships": mems,
        }


def _extract_token(headers: Dict[str, str]) -> Optional[str]:
    cookie = headers.get("cookie") or headers.get("Cookie") or ""
    for part in cookie.split(";"):
        part = part.strip()
        if part.startswith("medilocker_session="):
            return part.split("=", 1)[1].strip()
    auth_h = headers.get("authorization") or headers.get("Authorization") or ""
    if auth_h.lower().startswith("bearer "):
        return auth_h[7:].strip()
    return None


def _run_privacy_job(dataset_id: str, org_id: str, input_dir: Path, ds_name: str, user: Dict[str, Any]) -> Dict[str, Any]:
    job_id = f"job-{int(time.time())}-{secrets.token_hex(4)}"
    job_out = _APP_DIR / "jobs" / job_id / "output"
    job_out.mkdir(parents=True, exist_ok=True)
    now = time.time()

    with _get_db() as conn:
        conn.execute(
            "INSERT INTO jobs (id, dataset_id, organisation_id, input_name, status, current_stage, created_at) VALUES (?, ?, ?, ?, 'PROCESSING', 'PROCESSING', ?)",
            (job_id, dataset_id, org_id, ds_name, now),
        )

    # Invoke real starter/main.py in-process
    t0 = time.monotonic()
    prev_argv = sys.argv
    try:
        sys.argv = ["main.py", "--input", str(input_dir), "--output", str(job_out)]
        rc = engine_main.main()
    finally:
        sys.argv = prev_argv
    dur = round(time.monotonic() - t0, 2)

    if rc != 0 or not (job_out / "report.json").is_file():
        with _get_db() as conn:
            conn.execute("UPDATE jobs SET status = 'BLOCKED', release_decision = 'BLOCKED', completed_at = ?, duration_secs = ? WHERE id = ?", (time.time(), dur, job_id))
        return {"id": job_id, "status": "BLOCKED", "release_decision": "BLOCKED"}

    report = json.loads((job_out / "report.json").read_text(encoding="utf-8"))
    counts = report.get("counts", {})
    pi = report.get("privacy_intelligence", {})

    # Clinical drift
    in_texts = [p.read_text(encoding="utf-8", errors="ignore") for p in sorted(input_dir.rglob("*")) if p.is_file() and p.suffix.lower() in {".txt", ".csv", ".tsv", ".json"}]
    san_dir = job_out / "sanitized"
    san_texts = [p.read_text(encoding="utf-8", errors="ignore") for p in sorted(san_dir.rglob("*")) if p.is_file()] if san_dir.is_dir() else []
    fhir_bundles = []
    if san_dir.is_dir():
        for p in sorted(san_dir.rglob("*.json")):
            try:
                obj = json.loads(p.read_text(encoding="utf-8"))
                if isinstance(obj, dict) and obj.get("resourceType") == "Bundle":
                    fhir_bundles.append(obj)
            except Exception:
                pass
    drift = analyze_clinical_drift(in_texts, san_texts, fhir_bundles=fhir_bundles)
    ov = drift["overall"]

    # Attack summary from report
    atk = pi.get("attack_simulation", {})
    post_uniq = int(atk.get("post_uniquely_distinguishable", 0) or 0)
    recs_total = max(1, int(counts.get("records_processed", 0) or 0))
    risk_score = round((post_uniq / recs_total) * 100.0, 2)
    post_cats = (pi.get("risk_summary") or {}).get("post_categories") or {}
    crit_cnt = int(post_cats.get("CRITICAL", 0) or 0)
    high_cnt = int(post_cats.get("HIGH", 0) or 0)

    files_san = int(counts.get("files_sanitized", 0) or 0)
    files_quar = int(counts.get("files_quarantined", 0) or 0)
    if crit_cnt > 0 or ov["modified"] > 0 or not drift["passed"] and ov["missing"] > 0:
        rel_dec = "BLOCKED"
        final_st = "BLOCKED"
    elif files_quar > 0 or high_cnt > 0:
        rel_dec = "APPROVED_WITH_WARNINGS"
        final_st = "COMPLETED_WITH_WARNINGS"
    else:
        rel_dec = "APPROVED"
        final_st = "COMPLETED"

    pp_file = job_out / "privacy_passport.json"
    pp_data = json.loads(pp_file.read_text(encoding="utf-8")) if pp_file.is_file() else {}
    pp_id = (pp_data.get("certificate_identity") or {}).get("certificate_id") or f"psp-{secrets.token_hex(6)}"
    m_hash = (pp_data.get("dataset_provenance") or {}).get("output_dataset_root_hash") or hashlib.sha256(json.dumps(pp_data, sort_keys=True).encode()).hexdigest()
    sig_st = (pp_data.get("signature") or {}).get("status") or "UNSIGNED"

    fin_t = time.time()
    with _get_db() as conn:
        conn.execute(
            """UPDATE jobs SET status=?, current_stage=?, release_decision=?, files_total=?, files_sanitized=?,
            files_quarantined=?, records_processed=?, records_linked=?, identifiers_detected=?, duration_secs=?, completed_at=? WHERE id=?""",
            (final_st, final_st, rel_dec, counts.get("files_total", 0), files_san, files_quar, counts.get("records_processed", 0), counts.get("records_linked", 0), counts.get("identifiers_detected", 0), dur, fin_t, job_id),
        )
        conn.execute(
            """INSERT OR REPLACE INTO privacy_assessments (id, job_id, dataset_id, organisation_id, pii_detected, residual_leakage, canary_planted, canary_leaks, canary_status, qi_risk_score, reid_risk_level, release_eligible, details_json, created_at)
            VALUES (?, ?, ?, ?, ?, 0, 0, 0, 'NOT_RUN', ?, ?, ?, ?, ?)""",
            (f"pa-{secrets.token_hex(6)}", job_id, dataset_id, org_id, counts.get("identifiers_detected", 0), risk_score, "CRITICAL" if crit_cnt else ("HIGH" if high_cnt else "LOW"), 1 if rel_dec.startswith("APPROVED") else 0, json.dumps({"risk_map": {"low": int(post_cats.get("LOW", 0)), "moderate": int(post_cats.get("MODERATE", 0)), "high": high_cnt, "critical": crit_cnt, "total_assessed": sum(int(v) for v in post_cats.values()), "requiring_mitigation": int((pi.get("risk_summary") or {}).get("records_below_min_group_pre", 0)), "blocked_from_release": crit_cnt if rel_dec == "BLOCKED" else 0, "release_decision": rel_dec}}), fin_t),
        )
        conn.execute(
            """INSERT OR REPLACE INTO clinical_reports (id, job_id, organisation_id, expected_values, preserved_values, modified_values, missing_values, fhir_integrity, details_json, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (f"clin-{secrets.token_hex(6)}", job_id, org_id, ov["expected"], ov["preserved"], ov["modified"], ov["missing"], "PASS" if drift["fhir_failures"] == 0 else "FAILED", json.dumps(drift), fin_t),
        )
        conn.execute(
            "INSERT OR REPLACE INTO passports (id, job_id, dataset_id, organisation_id, manifest_hash, signature_status, passport_json, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            (pp_id, job_id, dataset_id, org_id, m_hash, sig_st, json.dumps(pp_data), fin_t),
        )
        conn.execute("UPDATE organisations SET records_contributed = records_contributed + ? WHERE id = ?", (counts.get("records_processed", 0), org_id))

    _audit("JOB_COMPLETED", "job", job_id, final_st, f"Processed {counts.get('files_total', 0)} files offline on Android.", user, org_id)
    return {"id": job_id, "status": final_st, "release_decision": rel_dec, "files_sanitized": files_san, "files_quarantined": files_quar}


def handle_request(method: str, path: str, query_string: str, headers_json: str, body_b64: str) -> Dict[str, Any]:
    """Unified HTTP router called by NanoHTTPD on Android."""
    headers = json.loads(headers_json) if headers_json else {}
    body = base64.b64decode(body_b64) if body_b64 else b""
    qs = parse_qs(query_string or "")

    def resp(status: int, data: Any, extra_headers: Optional[Dict[str, str]] = None) -> Dict[str, Any]:
        return {
            "status": status,
            "content_type": "application/json",
            "headers": extra_headers or {},
            "body_b64": base64.b64encode(json.dumps(data).encode("utf-8")).decode("ascii"),
        }

    # Public auth & health endpoints
    if path == "/api/health":
        return resp(200, {"status": "healthy", "mode": "android-offline-cpu", "engine": "GuptKavach In-Process Chaquopy"})

    if path == "/api/auth/config":
        return resp(200, {"offline_mode": True, "dev_login_enabled": True, "google_oauth_enabled": False, "smtp_configured": False})

    if path in ("/api/auth/offline-demo", "/api/auth/dev-login") and method == "POST":
        payload = json.loads(body.decode("utf-8")) if body else {}
        tok, ctx = _create_offline_session(payload.get("email", "privacy@metrogeneral.org"))
        cookie_hdr = {"Set-Cookie": f"medilocker_session={tok}; Path=/; HttpOnly; SameSite=Lax"}
        _audit("USER_LOGIN", "session", ctx["id"], "SUCCESS", "Offline Android local session started.", ctx)
        return resp(200, {"user": ctx, "token": tok}, cookie_hdr)

    # Require authenticated session for all protected routes
    tok = _extract_token(headers)
    user = _load_user_from_token(tok)
    if not user:
        return resp(401, {"detail": "Not authenticated"})

    if path == "/api/auth/me":
        return resp(200, {"user": user})

    if path == "/api/auth/logout" and method == "POST":
        if tok:
            with _get_db() as conn:
                conn.execute("UPDATE sessions SET revoked_at = ? WHERE token_hash = ?", (time.time(), _hash_token(tok)))
        return resp(200, {"status": "logged_out"}, {"Set-Cookie": "medilocker_session=; Path=/; Max-Age=0"})

    if path == "/api/auth/switch-org" and method == "POST":
        payload = json.loads(body.decode("utf-8")) if body else {}
        org_id = payload.get("organisation_id")
        if tok and org_id:
            with _get_db() as conn:
                conn.execute("UPDATE sessions SET active_org_id = ? WHERE token_hash = ?", (org_id, _hash_token(tok)))
        return resp(200, {"status": "switched", "active_org_id": org_id})

    org_id = user["active_org_id"]

    if path in ("/api/dashboard", "/api/dashboard/overview"):
        with _get_db() as conn:
            jobs = [dict(r) for r in conn.execute("SELECT * FROM jobs WHERE organisation_id = ? ORDER BY created_at DESC LIMIT 10", (org_id,)).fetchall()]
            pa = conn.execute("SELECT * FROM privacy_assessments WHERE organisation_id = ? ORDER BY created_at DESC LIMIT 1", (org_id,)).fetchone()
            cr = conn.execute("SELECT * FROM clinical_reports WHERE organisation_id = ? ORDER BY created_at DESC LIMIT 1", (org_id,)).fetchone()
            aud = [dict(r) for r in conn.execute("SELECT * FROM audit_events ORDER BY timestamp DESC LIMIT 10").fetchall()]
        latest = jobs[0] if jobs else None
        return resp(200, {
            "metrics": {
                "files_processed": {"value": latest["files_total"] if latest else 0, "display": str(latest["files_total"]) if latest else "0", "status": "PASS" if latest else "NOT_RUN", "description": "Latest job files"},
                "records_processed": {"value": latest["records_processed"] if latest else 0, "display": str(latest["records_processed"]) if latest else "0", "status": "PASS" if latest else "NOT_RUN", "description": "Records processed"},
                "pii_detected": {"value": pa["pii_detected"] if pa else None, "display": str(pa["pii_detected"]) if pa else "Not measured", "status": "PASS" if pa else "NOT_MEASURED", "description": "PII tokens redacted"},
                "clinical_preserved": {"value": cr["preserved_values"] if cr else None, "expected": cr["expected_values"] if cr else None, "display": f"{cr['preserved_values']}/{cr['expected_values']}" if cr else "Not measured", "status": "PASS" if cr else "NOT_MEASURED", "description": "Exact clinical fidelity"},
                "identity_precision": {"value": None, "display": "Not measured", "status": "NOT_MEASURED", "description": "Ground truth test-only"},
                "canary_leaks": {"value": pa["canary_leaks"] if pa else None, "display": "Not tested", "status": "NOT_RUN", "description": "Canary checks"},
            },
            "privacy_health": {"overall_readiness": latest["release_decision"] if latest else "NOT_RUN"},
            "recent_jobs": jobs,
            "audit_events": aud,
        })

    if path == "/api/organisations" and method == "GET":
        with _get_db() as conn:
            return resp(200, [dict(r) for r in conn.execute("SELECT * FROM organisations ORDER BY joined_at ASC").fetchall()])

    if path == "/api/organisations" and method == "POST":
        payload = json.loads(body.decode("utf-8")) if body else {}
        name = (payload.get("name") or "").strip()
        if not name:
            return resp(400, {"detail": "Organisation name is required"})
        new_org_id = f"org-{secrets.token_hex(4)}"
        with _get_db() as conn:
            conn.execute(
                "INSERT INTO organisations (id, name, org_type, region, status, records_contributed, joined_at) VALUES (?, ?, ?, ?, 'ACTIVE', 0, ?)",
                (new_org_id, name, payload.get("org_type", "Hospital"), payload.get("region", "India"), time.time()),
            )
            row = conn.execute("SELECT * FROM organisations WHERE id = ?", (new_org_id,)).fetchone()
        return resp(200, dict(row))

    if path == "/api/datasets" and method == "GET":
        with _get_db() as conn:
            return resp(200, [dict(r) for r in conn.execute("SELECT * FROM datasets WHERE organisation_id = ? ORDER BY created_at DESC", (org_id,)).fetchall()])

    if path == "/api/datasets" and method == "POST":
        ct_hdr = ""
        for hk, hv in headers.items():
            if hk.lower() == "content-type":
                ct_hdr = hv
                break
        if "multipart/form-data" not in ct_hdr.lower():
            return resp(400, {"detail": "Expected multipart/form-data upload"})
        msg = BytesParser(policy=email_default_policy).parsebytes(
            b"Content-Type: " + ct_hdr.encode("latin-1") + b"\r\n\r\n" + body
        )
        form_fields: Dict[str, str] = {}
        uploaded_files: List[Tuple[str, bytes]] = []
        allowed_exts = {".csv", ".tsv", ".json", ".jsonl", ".txt"}
        for part in msg.iter_parts():
            cd = part.get("Content-Disposition", "")
            field_name = part.get_param("name", header="Content-Disposition")
            filename = part.get_filename()
            payload_bytes = part.get_payload(decode=True) or b""
            if filename:
                ext = Path(filename).suffix.lower()
                if ext not in allowed_exts:
                    return resp(400, {"detail": f"Unsupported file format: {ext or 'unknown'}"})
                if len(payload_bytes) == 0:
                    return resp(400, {"detail": f"Empty file is not allowed: {filename}"})
                raw_base = filename.replace("\\", "/").split("/")[-1]
                safe_name = re.sub(r'[<>:"/\\|?*\x00-\x1f]', "_", raw_base).lstrip(".") or f"upload_{len(uploaded_files)}{ext}"
                uploaded_files.append((safe_name, payload_bytes))
            elif field_name:
                form_fields[field_name] = payload_bytes.decode("utf-8", errors="replace")

        if not uploaded_files:
            return resp(400, {"detail": "At least one file is required"})

        target_org = form_fields.get("organisation_id") or org_id
        ds_id = f"ds-{int(time.time())}-{secrets.token_hex(4)}"
        ds_dir = _APP_DIR / "datasets" / ds_id
        ds_dir.mkdir(parents=True, exist_ok=True)
        total_bytes = 0
        for safe_name, content in uploaded_files:
            (ds_dir / safe_name).write_bytes(content)
            total_bytes += len(content)

        ds_name = (form_fields.get("name") or "").strip() or (
            uploaded_files[0][0] if len(uploaded_files) == 1 else f"Batch ({len(uploaded_files)} files)"
        )
        with _get_db() as conn:
            conn.execute(
                "INSERT INTO datasets (id, organisation_id, name, status, files_count, total_bytes, storage_path, created_by, created_at) VALUES (?, ?, ?, 'VALIDATED', ?, ?, ?, ?, ?)",
                (ds_id, target_org, ds_name, len(uploaded_files), total_bytes, str(ds_dir), user["id"], time.time()),
            )
        _audit("DATASET_UPLOADED", "dataset", ds_id, "SUCCESS", f"Uploaded {len(uploaded_files)} file(s), {total_bytes} bytes", user, target_org)

        auto_proc = form_fields.get("auto_process", "true").lower() not in ("false", "0", "no")
        job = _run_privacy_job(ds_id, target_org, ds_dir, ds_name, user) if auto_proc else None
        return resp(200, {"dataset_id": ds_id, "job": job})

    if path.startswith("/api/datasets/") and path != "/api/datasets/process-sample" and method == "GET":
        ds_id = path.split("/")[3]
        with _get_db() as conn:
            row = conn.execute("SELECT * FROM datasets WHERE id = ? AND organisation_id = ?", (ds_id, org_id)).fetchone()
            if not row:
                return resp(404, {"detail": "Dataset not found"})
            ds_jobs = [dict(r) for r in conn.execute("SELECT * FROM jobs WHERE dataset_id = ? ORDER BY created_at DESC", (ds_id,)).fetchall()]
        d = dict(row)
        d["jobs"] = ds_jobs
        return resp(200, d)

    if path.startswith("/api/datasets/") and path != "/api/datasets/process-sample" and method == "DELETE":
        ds_id = path.split("/")[3]
        with _get_db() as conn:
            row = conn.execute("SELECT * FROM datasets WHERE id = ? AND organisation_id = ?", (ds_id, org_id)).fetchone()
            if not row:
                return resp(404, {"detail": "Dataset not found"})
            conn.execute("DELETE FROM datasets WHERE id = ?", (ds_id,))
        ds_path = Path(row["storage_path"])
        if ds_path.exists() and ds_path.is_dir():
            shutil.rmtree(ds_path, ignore_errors=True)
        return resp(200, {"status": "deleted"})

    if path == "/api/datasets/process-sample" and method == "POST":
        # Built-in synthetic offline sample trigger for Android verification
        ds_id = f"ds-{secrets.token_hex(5)}"
        ds_dir = _APP_DIR / "datasets" / ds_id
        ds_dir.mkdir(parents=True, exist_ok=True)
        (ds_dir / "synthetic_opd.csv").write_text(
            "patient_name,age,gender,district,phone,diagnosis,medication\n"
            "Amit Kumar,42,M,Jaipur,9876543210,Dengue fever,Paracetamol 500 mg\n"
            "Sunita Devi,43,F,Jaipur,9876543211,Typhoid,Azithromycin 500 mg\n"
            "Ramesh Sharma,41,M,Jaipur,9876543212,Hypertension,Amlodipine 5 mg\n"
            "Priya Verma,44,F,Jaipur,9876543213,Diabetes,Metformin 500 mg\n"
            "Mohan Lal,40,M,Jaipur,9876543214,Asthma,Salbutamol 100 mcg\n",
            encoding="utf-8",
        )
        with _get_db() as conn:
            conn.execute("INSERT INTO datasets (id, organisation_id, name, status, files_count, total_bytes, storage_path, created_by, created_at) VALUES (?, ?, 'Synthetic Offline Cohort', 'VALIDATED', 1, 350, ?, ?, ?)", (ds_id, org_id, str(ds_dir), user["id"], time.time()))
        job = _run_privacy_job(ds_id, org_id, ds_dir, "Synthetic Offline Cohort", user)
        return resp(200, {"dataset_id": ds_id, "job": job})

    if path == "/api/jobs" and method == "GET":
        with _get_db() as conn:
            return resp(200, [dict(r) for r in conn.execute("SELECT * FROM jobs WHERE organisation_id = ? ORDER BY created_at DESC", (org_id,)).fetchall()])

    if path == "/api/jobs" and method == "POST":
        payload = json.loads(body.decode("utf-8")) if body else {}
        ds_id = payload.get("dataset_id")
        with _get_db() as conn:
            ds = conn.execute("SELECT * FROM datasets WHERE id = ? AND organisation_id = ?", (ds_id, org_id)).fetchone()
        if not ds:
            return resp(404, {"detail": "Dataset not found"})
        job = _run_privacy_job(ds_id, org_id, Path(ds["storage_path"]), ds["name"], user)
        return resp(200, job)

    if path.startswith("/api/jobs/") and path.endswith("/download") and method == "GET":
        jid = path.split("/")[3]
        if not re.fullmatch(r"[A-Za-z0-9_.-]+", jid):
            return resp(400, {"detail": "Invalid job id"})
        with _get_db() as conn:
            jrow = conn.execute("SELECT * FROM jobs WHERE id = ? AND organisation_id = ?", (jid, org_id)).fetchone()
        if not jrow:
            return resp(404, {"detail": "Job not found"})
        job_out = _APP_DIR / "jobs" / jid / "output"
        if not job_out.exists():
            return resp(404, {"detail": "Job output not found"})
        buf = io.BytesIO()
        with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
            for fp in job_out.rglob("*"):
                if not fp.is_file():
                    continue
                rel = fp.relative_to(job_out).as_posix()
                # Never expose internal records.jsonl or quarantined source files
                if rel == "records.jsonl" or rel.endswith("/records.jsonl") or rel.startswith("quarantine/"):
                    continue
                zf.write(fp, rel)
        return {
            "status": 200,
            "content_type": "application/zip",
            "headers": {"Content-Disposition": f'attachment; filename="{jid}_sanitized.zip"'},
            "body_b64": base64.b64encode(buf.getvalue()).decode("ascii"),
        }

    if path.startswith("/api/jobs/") and path.endswith("/events") and method == "GET":
        jid = path.split("/")[3]
        with _get_db() as conn:
            jrow = conn.execute("SELECT * FROM jobs WHERE id = ? AND organisation_id = ?", (jid, org_id)).fetchone()
        if not jrow:
            return resp(404, {"detail": "Job not found"})
        return resp(200, [{"stage": "COMPLETED", "status": jrow["status"], "message": f"Release: {jrow['release_decision']}", "created_at": jrow["completed_at"] or jrow["created_at"]}])

    if path.startswith("/api/jobs/") and path.endswith("/results") and method == "GET":
        jid = path.split("/")[3]
        with _get_db() as conn:
            jrow = conn.execute("SELECT * FROM jobs WHERE id = ? AND organisation_id = ?", (jid, org_id)).fetchone()
            if not jrow:
                return resp(404, {"detail": "Job not found"})
            pa = conn.execute("SELECT * FROM privacy_assessments WHERE job_id = ?", (jid,)).fetchone()
            cr = conn.execute("SELECT * FROM clinical_reports WHERE job_id = ?", (jid,)).fetchone()
            pp = conn.execute("SELECT * FROM passports WHERE job_id = ?", (jid,)).fetchone()
        return resp(200, {
            "job": dict(jrow),
            "privacy_assessment": dict(pa) if pa else None,
            "clinical_report": dict(cr) if cr else None,
            "identity_cluster": {"status": "MEASURED", "records_linked": jrow["records_linked"], "precision": "NOT_MEASURED"},
            "passport": dict(pp) if pp else None,
        })

    if path.startswith("/api/jobs/") and method == "GET":
        jid = path.split("/")[3]
        with _get_db() as conn:
            row = conn.execute("SELECT * FROM jobs WHERE id = ? AND organisation_id = ?", (jid, org_id)).fetchone()
        if not row:
            return resp(404, {"detail": "Job not found"})
        return resp(200, dict(row))

    if path == "/api/privacy-intelligence":
        with _get_db() as conn:
            rows = [dict(r) for r in conn.execute("SELECT * FROM privacy_assessments WHERE organisation_id = ? ORDER BY created_at DESC", (org_id,)).fetchall()]
        if not rows:
            return resp(200, {"status": "NOT_MEASURED", "assessments_count": 0, "total_pii_detected": 0, "total_residual_leakage": 0, "canary_status": "NOT_RUN", "reid_risk_level": "NOT_MEASURED", "assessments": []})
        latest = rows[0]
        rmap = json.loads(latest.get("details_json") or "{}").get("risk_map")
        return resp(200, {"status": "MEASURED", "assessments_count": len(rows), "total_pii_detected": sum(r["pii_detected"] for r in rows), "total_residual_leakage": sum(r["residual_leakage"] for r in rows), "canary_status": latest["canary_status"], "reid_risk_level": latest["reid_risk_level"], "risk_map": rmap, "assessments": rows})

    if path == "/api/quarantine":
        req_jid = (qs.get("job_id") or [None])[0]
        with _get_db() as conn:
            jrow = conn.execute("SELECT * FROM jobs WHERE id = ? AND organisation_id = ?", (req_jid, org_id)).fetchone() if req_jid else conn.execute("SELECT * FROM jobs WHERE organisation_id = ? ORDER BY created_at DESC LIMIT 1", (org_id,)).fetchone()
        if not jrow:
            return resp(200, {"status": "NOT_RUN", "items": [], "total_quarantined": 0})
        rep_path = _APP_DIR / "jobs" / jrow["id"] / "output" / "report.json"
        items: List[Dict[str, Any]] = []
        if rep_path.is_file():
            rep = json.loads(rep_path.read_text(encoding="utf-8"))
            for qf in (rep.get("quarantined_files") or rep.get("quarantine") or []):
                if isinstance(qf, dict):
                    items.append({"filename": Path(str(qf.get("file", qf.get("filename", "unknown")))).name, "reason": qf.get("reason", "Quarantined by engine"), "status": "QUARANTINED"})
                else:
                    items.append({"filename": Path(str(qf)).name, "reason": "Quarantined by engine", "status": "QUARANTINED"})
        return resp(200, {"status": "MEASURED", "job_id": jrow["id"], "total_quarantined": jrow["files_quarantined"], "items": items})

    if path in ("/api/identity/clusters", "/api/identity-graph"):
        req_jid = (qs.get("job_id") or [None])[0]
        with _get_db() as conn:
            jrow = conn.execute("SELECT * FROM jobs WHERE id = ? AND organisation_id = ?", (req_jid, org_id)).fetchone() if req_jid else conn.execute("SELECT * FROM jobs WHERE organisation_id = ? ORDER BY created_at DESC LIMIT 1", (org_id,)).fetchone()
        if not jrow:
            return resp(200, {"status": "NOT_MEASURED", "precision": "NOT_MEASURED", "clusters": [], "records_linked": 0})
        return resp(200, {"status": "MEASURED", "job_id": jrow["id"], "precision": "NOT_MEASURED", "records_processed": jrow["records_processed"], "records_linked": jrow["records_linked"], "clusters": []})

    if path in ("/api/threat-lab", "/api/attack-simulator/run"):
        with _get_db() as conn:
            jrow = conn.execute("SELECT * FROM jobs WHERE organisation_id = ? ORDER BY created_at DESC LIMIT 1", (org_id,)).fetchone()
        if not jrow:
            return resp(200, {"status": "NOT_RUN", "vectors": [], "summary": {}})
        pi_path = _APP_DIR / "jobs" / jrow["id"] / "output" / "privacy_intelligence.json"
        pi_data = json.loads(pi_path.read_text(encoding="utf-8")) if pi_path.is_file() else {}
        atk = pi_data.get("attack_simulation") or {}
        return resp(200, {"status": "EXECUTED", "job_id": jrow["id"], "attack_simulation": atk, "risk_summary": pi_data.get("risk_summary") or {}})

    if path == "/api/privacy/assessments":
        with _get_db() as conn:
            return resp(200, [dict(r) for r in conn.execute("SELECT * FROM privacy_assessments WHERE organisation_id = ? ORDER BY created_at DESC", (org_id,)).fetchall()])

    if path.startswith("/api/privacy/assessments/") and method == "GET":
        aid = path.split("/")[4]
        with _get_db() as conn:
            row = conn.execute("SELECT * FROM privacy_assessments WHERE id = ? AND organisation_id = ?", (aid, org_id)).fetchone()
        return resp(200, dict(row)) if row else resp(404, {"detail": "Assessment not found"})

    if path in ("/api/clinical-reports", "/api/clinical/reports") and method == "GET":
        with _get_db() as conn:
            return resp(200, [dict(r) for r in conn.execute("SELECT * FROM clinical_reports WHERE organisation_id = ? ORDER BY created_at DESC", (org_id,)).fetchall()])

    if path.startswith("/api/clinical/reports/") and method == "GET":
        cid = path.split("/")[4]
        with _get_db() as conn:
            row = conn.execute("SELECT * FROM clinical_reports WHERE id = ? AND organisation_id = ?", (cid, org_id)).fetchone()
        return resp(200, dict(row)) if row else resp(404, {"detail": "Clinical report not found"})

    if path == "/api/passports":
        with _get_db() as conn:
            return resp(200, [dict(r) for r in conn.execute("SELECT * FROM passports WHERE organisation_id = ? ORDER BY created_at DESC", (org_id,)).fetchall()])

    if path.startswith("/api/passports/") and path.endswith("/download") and method == "GET":
        pid = path.split("/")[3]
        fmt = (qs.get("format") or ["json"])[0].lower()
        with _get_db() as conn:
            row = conn.execute("SELECT * FROM passports WHERE id = ? AND organisation_id = ?", (pid, org_id)).fetchone()
        if not row:
            return resp(404, {"detail": "Passport not found"})
        if fmt == "html":
            pp = json.loads(row["passport_json"] or "{}")
            html = f"<html><body><h1>MediLocker Privacy Passport</h1><p>ID: {pid}</p><p>Status: {row['signature_status']}</p><pre>{json.dumps(pp, indent=2)}</pre></body></html>"
            return {"status": 200, "content_type": "text/html; charset=utf-8", "headers": {"Content-Disposition": f'attachment; filename="{pid}.html"'}, "body_b64": base64.b64encode(html.encode("utf-8")).decode("ascii")}
        return {"status": 200, "content_type": "application/json", "headers": {"Content-Disposition": f'attachment; filename="{pid}.json"'}, "body_b64": base64.b64encode((row["passport_json"] or "{}").encode("utf-8")).decode("ascii")}

    if path.startswith("/api/passports/") and path.endswith("/verify") and method == "POST":
        pid = path.split("/")[3]
        with _get_db() as conn:
            row = conn.execute("SELECT * FROM passports WHERE id = ? AND organisation_id = ?", (pid, org_id)).fetchone()
        if not row:
            return resp(404, {"detail": "Passport not found"})
        job_out = _APP_DIR / "jobs" / row["job_id"] / "output"
        vres = verify_passport_bundle(job_out / "privacy_passport.json", job_out, manifest_path=job_out / "dataset_manifest.json")
        return resp(200, {"passport_id": pid, "integrity_valid": bool(vres.get("valid")), "signature_status": row["signature_status"], "manifest_hash": row["manifest_hash"], "details": vres.get("details", [])})

    if path.startswith("/api/passports/") and method == "GET":
        pid = path.split("/")[3]
        with _get_db() as conn:
            row = conn.execute("SELECT * FROM passports WHERE id = ? AND organisation_id = ?", (pid, org_id)).fetchone()
        return resp(200, dict(row)) if row else resp(404, {"detail": "Passport not found"})

    if path in ("/api/audit", "/api/audit/events"):
        with _get_db() as conn:
            return resp(200, [dict(r) for r in conn.execute("SELECT * FROM audit_events ORDER BY timestamp DESC LIMIT 50").fetchall()])

    if path in ("/api/research-requests", "/api/research/requests") and method == "GET":
        with _get_db() as conn:
            return resp(200, [dict(r) for r in conn.execute("SELECT * FROM research_requests ORDER BY created_at DESC").fetchall()])

    if path == "/api/research/requests" and method == "POST":
        payload = json.loads(body.decode("utf-8")) if body else {}
        rid = f"req-{secrets.token_hex(4)}"
        with _get_db() as conn:
            conn.execute(
                "INSERT INTO research_requests (id, title, requestor_org, target_orgs, dataset_id, purpose, status, created_at) VALUES (?, ?, ?, ?, ?, ?, 'PENDING', ?)",
                (rid, payload.get("title", "Research Study"), payload.get("requestor_org", "Research Partner"), json.dumps(payload.get("target_orgs", [])), payload.get("dataset_id", ""), payload.get("purpose", ""), time.time()),
            )
            row = conn.execute("SELECT * FROM research_requests WHERE id = ?", (rid,)).fetchone()
        return resp(200, dict(row))

    if path.startswith("/api/research/requests/") and (path.endswith("/approve") or path.endswith("/reject")) and method == "POST":
        rid = path.split("/")[4]
        new_st = "APPROVED" if path.endswith("/approve") else "REJECTED"
        with _get_db() as conn:
            conn.execute("UPDATE research_requests SET status = ? WHERE id = ?", (new_st, rid))
            row = conn.execute("SELECT * FROM research_requests WHERE id = ?", (rid,)).fetchone()
        return resp(200, dict(row)) if row else resp(404, {"detail": "Request not found"})

    if path == "/api/settings" and method == "GET":
        return resp(200, {"offline_mode": True, "cpu_only": True, "policy": {"date_shift_max_days": 180, "min_group_size": 5, "age_band_width": 5}})

    if path == "/api/settings" and method == "POST":
        payload = json.loads(body.decode("utf-8")) if body else {}
        ds_days = int(payload.get("date_shift_max_days", 180))
        mg_size = int(payload.get("min_group_size", 5))
        ab_width = int(payload.get("age_band_width", 5))
        if not (1 <= ds_days <= 365) or mg_size < 2 or not (1 <= ab_width <= 20):
            return resp(400, {"detail": "Invalid privacy policy parameters"})
        return resp(200, {"offline_mode": True, "cpu_only": True, "policy": {"date_shift_max_days": ds_days, "min_group_size": mg_size, "age_band_width": ab_width}})

    if path == "/api/system/diagnostics":
        return resp(200, {"offline_mode": True, "cpu_only": True, "engine_loaded": True, "db_path": str(_DB_PATH), "storage_ready": _APP_DIR.exists()})

    return resp(404, {"detail": f"Endpoint not found: {path}"})
