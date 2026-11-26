"""SQLite Database Layer for GuptKavach Console Metadata.
Stores only non-sensitive operational metadata (job IDs, hashes, timestamps, policy versions, synthetic orgs).
Never stores RAKSHA_SECRET or raw patient identifiers.
"""
from __future__ import annotations

import json
import sqlite3
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

DB_PATH = Path(__file__).resolve().parent.parent / "data" / "guptkavach.db"
DB_PATH.parent.mkdir(parents=True, exist_ok=True)


def get_db() -> sqlite3.Connection:
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    return conn


def init_db() -> None:
    with get_db() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS jobs (
                id TEXT PRIMARY KEY,
                created_at REAL,
                status TEXT,
                input_name TEXT,
                files_total INTEGER DEFAULT 0,
                files_sanitized INTEGER DEFAULT 0,
                files_quarantined INTEGER DEFAULT 0,
                records_processed INTEGER DEFAULT 0,
                records_linked INTEGER DEFAULT 0,
                identifiers_detected INTEGER DEFAULT 0,
                duration_secs REAL DEFAULT 0.0,
                policy_version TEXT DEFAULT '1.0',
                error_msg TEXT
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS audit_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp REAL,
                event_type TEXT,
                job_id TEXT,
                description TEXT,
                file_hash TEXT,
                policy_version TEXT,
                status TEXT
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS organisations (
                id TEXT PRIMARY KEY,
                name TEXT,
                org_type TEXT,
                region TEXT,
                status TEXT,
                records_contributed INTEGER DEFAULT 0,
                joined_at REAL
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS research_requests (
                id TEXT PRIMARY KEY,
                title TEXT,
                requestor_org TEXT,
                target_orgs TEXT,
                purpose TEXT,
                status TEXT,
                created_at REAL,
                datasets_requested TEXT,
                release_simulated INTEGER DEFAULT 0
            )
        """)
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
                ("org-hosp-a", "Metro General Hospital", "Hospital", "Delhi NCR", "Active", 1250, now - 86400 * 30),
                ("org-hosp-b", "Apex Care Medical Centre", "Hospital", "Mumbai", "Active", 840, now - 86400 * 20),
                ("org-lab-c", "ThyroCare Bio Diagnostics", "Diagnostic Lab", "Bengaluru", "Active", 620, now - 86400 * 15),
                ("org-res-d", "National Institute of Epidemiology", "Research Institute", "Chennai", "Active", 0, now - 86400 * 10),
            ]
            conn.executemany(
                "INSERT INTO organisations (id, name, org_type, region, status, records_contributed, joined_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
                orgs
            )

        # Seed synthetic research requests if empty
        cur = conn.execute("SELECT COUNT(*) as cnt FROM research_requests")
        if cur.fetchone()["cnt"] == 0:
            now = time.time()
            requests = [
                (
                    "req-2026-001",
                    "Multi-Centric Type-2 Diabetes Longitudinal Study",
                    "National Institute of Epidemiology",
                    json.dumps(["Metro General Hospital", "Apex Care Medical Centre"]),
                    "Study cross-facility glycemic patterns and age-correlated drug response without patient re-identification.",
                    "Approved",
                    now - 86400 * 4,
                    json.dumps(["OPD Consultations (CSV)", "Lab Biopsy Panels (JSON)"]),
                    1
                ),
                (
                    "req-2026-002",
                    "Cardiovascular Event Retrospective Cohort",
                    "National Institute of Epidemiology",
                    json.dumps(["Metro General Hospital"]),
                    "Correlate pre-existing hypertension records with hospital admission events across clinical notes.",
                    "Pending",
                    now - 86400 * 1,
                    json.dumps(["Clinical Summaries (TXT)", "Discharge Summaries (FHIR)"]),
                    0
                )
            ]
            conn.executemany(
                "INSERT INTO research_requests (id, title, requestor_org, target_orgs, purpose, status, created_at, datasets_requested, release_simulated) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                requests
            )
