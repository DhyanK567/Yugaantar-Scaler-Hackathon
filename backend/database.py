"""SQLite Database Layer for GuptKavach / MediLocker Single Source of Truth.
Stores only non-sensitive operational metadata (IDs, hashes, timestamps, policy versions,
assessment summaries, release decisions, synthetic orgs, research requests, and audit events).
Never stores RAKSHA_SECRET or raw patient identifiers.
"""
from __future__ import annotations

import json
import os
import re
import sqlite3
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

DB_PATH = Path(__file__).resolve().parent.parent / "data" / "guptkavach.db"
DB_PATH.parent.mkdir(parents=True, exist_ok=True)

_RX_RAW_AADHAAR = re.compile(r"(?<!\d)\d{4}[\s-]?\d{4}[\s-]?\d{4}(?!\d)")
_RX_RAW_PHONE = re.compile(r"(?:\+91[\s-]?)?[6-9]\d{9}\b")
_RX_RAW_EMAIL = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")


def sanitize_log_text(text: str) -> str:
    """Redact accidental raw identifiers or secrets from audit descriptions/errors."""
    if not text:
        return ""
    out = _RX_RAW_AADHAAR.sub("[REDACTED_ID]", text)
    out = _RX_RAW_PHONE.sub("[REDACTED_PHONE]", out)
    out = _RX_RAW_EMAIL.sub("[REDACTED_EMAIL]", out)
    secret = os.environ.get("RAKSHA_SECRET", "")
    if secret and len(secret) >= 4:
        out = out.replace(secret, "[REDACTED_SECRET]")
    return out


def get_db() -> sqlite3.Connection:
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    return conn


def _ensure_columns(conn: sqlite3.Connection, table: str, cols: Dict[str, str]) -> None:
    existing = {row["name"] for row in conn.execute(f"PRAGMA table_info({table})").fetchall()}
    for col_name, col_def in cols.items():
        if col_name not in existing:
            conn.execute(f"ALTER TABLE {table} ADD COLUMN {col_name} {col_def}")


def init_db() -> None:
    with get_db() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS organisations (
                id TEXT PRIMARY KEY,
                name TEXT,
                org_type TEXT,
                region TEXT,
                status TEXT,
                records_contributed INTEGER DEFAULT 0,
                joined_at REAL,
                contact_role TEXT DEFAULT 'Privacy Officer'
            )
        """)
        _ensure_columns(conn, "organisations", {
            "contact_role": "TEXT DEFAULT 'Privacy Officer'",
        })

        conn.execute("""
            CREATE TABLE IF NOT EXISTS datasets (
                id TEXT PRIMARY KEY,
                org_id TEXT,
                name TEXT,
                source_type TEXT,
                storage_path TEXT,
                files_count INTEGER DEFAULT 0,
                total_bytes INTEGER DEFAULT 0,
                formats_json TEXT,
                manifest_sha256 TEXT,
                validation_status TEXT,
                validation_errors_json TEXT,
                created_at REAL
            )
        """)

        conn.execute("""
            CREATE TABLE IF NOT EXISTS jobs (
                id TEXT PRIMARY KEY,
                dataset_id TEXT,
                org_id TEXT,
                created_at REAL,
                status TEXT,
                current_stage TEXT,
                stage_history_json TEXT,
                input_name TEXT,
                output_dir TEXT,
                files_total INTEGER DEFAULT 0,
                files_sanitized INTEGER DEFAULT 0,
                files_quarantined INTEGER DEFAULT 0,
                records_processed INTEGER DEFAULT 0,
                records_linked INTEGER DEFAULT 0,
                identifiers_detected INTEGER DEFAULT 0,
                records_generalized INTEGER DEFAULT 0,
                records_suppressed INTEGER DEFAULT 0,
                duration_secs REAL DEFAULT 0.0,
                policy_version TEXT DEFAULT '1.0',
                privacy_assessment_ref TEXT,
                clinical_assessment_ref TEXT,
                identity_assessment_ref TEXT,
                attack_assessment_ref TEXT,
                passport_id TEXT,
                release_decision TEXT DEFAULT 'NOT_EVALUATED',
                error_msg TEXT
            )
        """)
        _ensure_columns(conn, "jobs", {
            "dataset_id": "TEXT",
            "org_id": "TEXT",
            "current_stage": "TEXT",
            "stage_history_json": "TEXT",
            "output_dir": "TEXT",
            "records_generalized": "INTEGER DEFAULT 0",
            "records_suppressed": "INTEGER DEFAULT 0",
            "privacy_assessment_ref": "TEXT",
            "clinical_assessment_ref": "TEXT",
            "identity_assessment_ref": "TEXT",
            "attack_assessment_ref": "TEXT",
            "passport_id": "TEXT",
            "release_decision": "TEXT DEFAULT 'NOT_EVALUATED'",
        })

        conn.execute("""
            CREATE TABLE IF NOT EXISTS attack_simulations (
                id TEXT PRIMARY KEY,
                job_id TEXT,
                org_id TEXT,
                dataset_id TEXT,
                executed_at REAL,
                total_records INTEGER DEFAULT 0,
                pre_uniquely_distinguishable INTEGER DEFAULT 0,
                post_uniquely_distinguishable INTEGER DEFAULT 0,
                vectors_json TEXT
            )
        """)

        conn.execute("""
            CREATE TABLE IF NOT EXISTS passports (
                passport_id TEXT PRIMARY KEY,
                job_id TEXT,
                dataset_id TEXT,
                org_id TEXT,
                policy_version TEXT,
                input_manifest_hash TEXT,
                output_manifest_hash TEXT,
                generated_at TEXT,
                release_decision TEXT,
                signature_status TEXT,
                verification_status TEXT,
                passport_json TEXT
            )
        """)

        conn.execute("""
            CREATE TABLE IF NOT EXISTS audit_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                event_id TEXT,
                timestamp REAL,
                event_type TEXT,
                actor TEXT DEFAULT 'local-privacy-officer',
                org_id TEXT,
                resource_id TEXT,
                job_id TEXT,
                description TEXT,
                file_hash TEXT,
                policy_version TEXT,
                status TEXT,
                outcome TEXT,
                safe_metadata TEXT
            )
        """)
        _ensure_columns(conn, "audit_logs", {
            "event_id": "TEXT",
            "actor": "TEXT DEFAULT 'local-privacy-officer'",
            "org_id": "TEXT",
            "resource_id": "TEXT",
            "outcome": "TEXT",
            "safe_metadata": "TEXT",
        })

        conn.execute("""
            CREATE TABLE IF NOT EXISTS research_requests (
                id TEXT PRIMARY KEY,
                title TEXT,
                requestor_org TEXT,
                target_orgs TEXT,
                dataset_id TEXT,
                job_id TEXT,
                purpose TEXT,
                status TEXT,
                created_at REAL,
                reviewed_at REAL,
                reviewed_by TEXT,
                datasets_requested TEXT,
                permitted_output_ref TEXT,
                release_simulated INTEGER DEFAULT 0
            )
        """)
        _ensure_columns(conn, "research_requests", {
            "dataset_id": "TEXT",
            "job_id": "TEXT",
            "reviewed_at": "REAL",
            "reviewed_by": "TEXT",
            "permitted_output_ref": "TEXT",
        })

        conn.execute("""
            CREATE TABLE IF NOT EXISTS settings (
                key TEXT PRIMARY KEY,
                value TEXT
            )
        """)

        # Seed synthetic organisations if empty
        cur = conn.execute("SELECT COUNT(*) as cnt FROM organisations")
        if cur.fetchone()["cnt"] == 0:
            now = time.time()
            orgs = [
                ("org-hosp-a", "Metro General Hospital (Hospital A)", "Hospital", "Delhi NCR", "Active", 0, now - 86400 * 30, "Chief Privacy Officer"),
                ("org-hosp-b", "Apex Care Medical Centre (Hospital B)", "Hospital", "Mumbai", "Active", 0, now - 86400 * 20, "Medical Records Lead"),
                ("org-hosp-c", "Sanjeevani Rural Health (Hospital C)", "Hospital", "Varanasi", "Active", 0, now - 86400 * 15, "Data Steward"),
                ("org-lab-d", "ThyroCare Bio Diagnostics (Lab D)", "Diagnostic Lab", "Bengaluru", "Active", 0, now - 86400 * 10, "Lab Compliance Officer"),
            ]
            conn.executemany(
                "INSERT INTO organisations (id, name, org_type, region, status, records_contributed, joined_at, contact_role) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                orgs,
            )

        # Seed synthetic research requests if empty
        cur = conn.execute("SELECT COUNT(*) as cnt FROM research_requests")
        if cur.fetchone()["cnt"] == 0:
            now = time.time()
            requests = [
                (
                    "req-2026-001",
                    "Multi-Centric Type-2 Diabetes Longitudinal Study",
                    "National Institute of Epidemiology (Synthetic)",
                    json.dumps(["Metro General Hospital (Hospital A)", "Apex Care Medical Centre (Hospital B)"]),
                    "practice-dev-dataset",
                    None,
                    "Study cross-facility glycemic patterns and age-correlated drug response without patient re-identification.",
                    "Pending",
                    now - 86400 * 2,
                    None,
                    None,
                    json.dumps(["OPD Consultations (CSV)", "Lab Biopsy Panels (JSON)"]),
                    None,
                    0,
                ),
            ]
            conn.executemany(
                """INSERT INTO research_requests (
                    id, title, requestor_org, target_orgs, dataset_id, job_id, purpose,
                    status, created_at, reviewed_at, reviewed_by, datasets_requested,
                    permitted_output_ref, release_simulated
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                requests,
            )


def record_audit_event(
    event_type: str,
    description: str,
    org_id: Optional[str] = None,
    resource_id: Optional[str] = None,
    job_id: Optional[str] = None,
    file_hash: str = "N/A",
    policy_version: str = "1.0",
    status: str = "RECORDED",
    outcome: str = "SUCCESS",
    actor: str = "local-privacy-officer",
    safe_metadata: Optional[Dict[str, Any]] = None,
) -> str:
    """Append an immutable audit event with automatic PII/secret scrubbing."""
    event_id = f"evt-{int(time.time() * 1000)}-{os.urandom(3).hex()}"
    safe_desc = sanitize_log_text(description)
    meta_json = json.dumps(safe_metadata or {}, ensure_ascii=False, sort_keys=True)
    meta_json = sanitize_log_text(meta_json)

    with get_db() as conn:
        conn.execute(
            """
            INSERT INTO audit_logs (
                event_id, timestamp, event_type, actor, org_id, resource_id, job_id,
                description, file_hash, policy_version, status, outcome, safe_metadata
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                event_id,
                time.time(),
                event_type,
                actor,
                org_id,
                resource_id,
                job_id,
                safe_desc,
                file_hash,
                policy_version,
                status,
                outcome,
                meta_json,
            ),
        )
    return event_id
