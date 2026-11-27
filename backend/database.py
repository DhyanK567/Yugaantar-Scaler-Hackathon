"""SQLite Database Layer & Migrations for MediLocker Platform.
Stores only non-sensitive operational metadata, hashed credentials/OTPs, and assessment results.
Never stores RAKSHA_SECRET, plaintext OTPs, or raw patient identifiers.
"""
from __future__ import annotations

import json
import os
import sqlite3
import time
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional

DEFAULT_DB_PATH = Path(__file__).resolve().parent.parent / "data" / "guptkavach.db"


def get_db_path() -> Path:
    override = os.environ.get("MEDILOCKER_DB_PATH")
    if override:
        p = Path(override)
    else:
        data_dir = os.environ.get("MEDILOCKER_DATA_DIR")
        p = (Path(data_dir) / "guptkavach.db") if data_dir else DEFAULT_DB_PATH
    p.parent.mkdir(parents=True, exist_ok=True)
    return p


def get_db() -> sqlite3.Connection:
    conn = sqlite3.connect(str(get_db_path()), timeout=30.0, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON;")
    conn.execute("PRAGMA journal_mode = WAL;")
    return conn


def _has_column(conn: sqlite3.Connection, table: str, column: str) -> bool:
    cols = conn.execute(f"PRAGMA table_info({table})").fetchall()
    return any(c["name"] == column for c in cols)


def _add_column_if_missing(conn: sqlite3.Connection, table: str, column: str, definition: str) -> None:
    if not _has_column(conn, table, column):
        conn.execute(f"ALTER TABLE {table} ADD COLUMN {column} {definition}")


def init_db() -> None:
    """Initialise database tables and run idempotent non-destructive migrations."""
    with get_db() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS schema_migrations (
                version TEXT PRIMARY KEY,
                applied_at REAL NOT NULL
            )
        """)

        # --- Organisations ---
        conn.execute("""
            CREATE TABLE IF NOT EXISTS organisations (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                org_type TEXT NOT NULL,
                region TEXT DEFAULT 'India',
                status TEXT DEFAULT 'Active',
                records_contributed INTEGER DEFAULT 0,
                joined_at REAL NOT NULL
            )
        """)

        # --- Users & RBAC Memberships ---
        conn.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id TEXT PRIMARY KEY,
                email TEXT UNIQUE NOT NULL,
                full_name TEXT NOT NULL,
                status TEXT DEFAULT 'ACTIVE',
                platform_role TEXT DEFAULT 'USER',
                created_at REAL NOT NULL,
                last_login_at REAL
            )
        """)
        conn.execute("CREATE INDEX IF NOT EXISTS idx_users_email ON users(email)")

        conn.execute("""
            CREATE TABLE IF NOT EXISTS memberships (
                id TEXT PRIMARY KEY,
                user_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                organisation_id TEXT NOT NULL REFERENCES organisations(id) ON DELETE CASCADE,
                role TEXT NOT NULL,
                created_at REAL NOT NULL,
                UNIQUE(user_id, organisation_id)
            )
        """)
        conn.execute("CREATE INDEX IF NOT EXISTS idx_memberships_user ON memberships(user_id)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_memberships_org ON memberships(organisation_id)")

        # --- Sessions ---
        conn.execute("""
            CREATE TABLE IF NOT EXISTS sessions (
                id TEXT PRIMARY KEY,
                token_hash TEXT UNIQUE NOT NULL,
                user_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                active_org_id TEXT REFERENCES organisations(id) ON DELETE SET NULL,
                expires_at REAL NOT NULL,
                revoked_at REAL,
                created_at REAL NOT NULL,
                ip_address TEXT,
                user_agent TEXT
            )
        """)
        conn.execute("CREATE INDEX IF NOT EXISTS idx_sessions_token ON sessions(token_hash)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_sessions_user ON sessions(user_id)")

        # --- Email OTP Challenges ---
        conn.execute("""
            CREATE TABLE IF NOT EXISTS otp_challenges (
                id TEXT PRIMARY KEY,
                email TEXT NOT NULL,
                purpose TEXT NOT NULL DEFAULT 'login',
                otp_hash TEXT NOT NULL,
                attempts INTEGER DEFAULT 0,
                max_attempts INTEGER DEFAULT 5,
                expires_at REAL NOT NULL,
                consumed_at REAL,
                created_at REAL NOT NULL,
                ip_address TEXT
            )
        """)
        conn.execute("CREATE INDEX IF NOT EXISTS idx_otp_email_purpose ON otp_challenges(email, purpose, created_at)")

        # --- Google OAuth Identities & States ---
        conn.execute("""
            CREATE TABLE IF NOT EXISTS oauth_identities (
                id TEXT PRIMARY KEY,
                user_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                provider TEXT NOT NULL,
                provider_sub TEXT NOT NULL,
                email TEXT NOT NULL,
                email_verified INTEGER NOT NULL DEFAULT 0,
                created_at REAL NOT NULL,
                UNIQUE(provider, provider_sub)
            )
        """)
        conn.execute("CREATE INDEX IF NOT EXISTS idx_oauth_user ON oauth_identities(user_id)")

        conn.execute("""
            CREATE TABLE IF NOT EXISTS oauth_states (
                state TEXT PRIMARY KEY,
                nonce TEXT NOT NULL,
                code_verifier TEXT NOT NULL,
                redirect_uri TEXT NOT NULL,
                link_user_id TEXT REFERENCES users(id) ON DELETE CASCADE,
                expires_at REAL NOT NULL,
                created_at REAL NOT NULL
            )
        """)

        # --- Datasets ---
        conn.execute("""
            CREATE TABLE IF NOT EXISTS datasets (
                id TEXT PRIMARY KEY,
                organisation_id TEXT NOT NULL REFERENCES organisations(id) ON DELETE CASCADE,
                name TEXT NOT NULL,
                description TEXT DEFAULT '',
                format TEXT NOT NULL,
                file_count INTEGER DEFAULT 0,
                total_bytes INTEGER DEFAULT 0,
                sha256 TEXT,
                storage_path TEXT,
                status TEXT DEFAULT 'VALIDATED',
                created_by TEXT REFERENCES users(id) ON DELETE SET NULL,
                created_at REAL NOT NULL,
                deleted_at REAL
            )
        """)
        _add_column_if_missing(conn, "datasets", "organisation_id", "TEXT")
        _add_column_if_missing(conn, "datasets", "description", "TEXT DEFAULT ''")
        _add_column_if_missing(conn, "datasets", "format", "TEXT DEFAULT 'CSV'")
        _add_column_if_missing(conn, "datasets", "file_count", "INTEGER DEFAULT 0")
        _add_column_if_missing(conn, "datasets", "sha256", "TEXT")
        _add_column_if_missing(conn, "datasets", "deleted_at", "REAL")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_datasets_org ON datasets(organisation_id)")

        # --- Processing Jobs (preserve existing table & migrate columns) ---
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
        _add_column_if_missing(conn, "jobs", "dataset_id", "TEXT")
        _add_column_if_missing(conn, "jobs", "organisation_id", "TEXT")
        _add_column_if_missing(conn, "jobs", "created_by", "TEXT")
        _add_column_if_missing(conn, "jobs", "started_at", "REAL")
        _add_column_if_missing(conn, "jobs", "completed_at", "REAL")
        _add_column_if_missing(conn, "jobs", "current_stage", "TEXT DEFAULT 'CREATED'")
        _add_column_if_missing(conn, "jobs", "release_decision", "TEXT DEFAULT 'PENDING'")
        _add_column_if_missing(conn, "jobs", "safe_error_code", "TEXT")
        _add_column_if_missing(conn, "jobs", "summary_json", "TEXT")
        _add_column_if_missing(conn, "jobs", "idempotency_key", "TEXT")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_jobs_org ON jobs(organisation_id)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_jobs_dataset ON jobs(dataset_id)")

        # --- Job Stage Events ---
        conn.execute("""
            CREATE TABLE IF NOT EXISTS job_events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                job_id TEXT NOT NULL REFERENCES jobs(id) ON DELETE CASCADE,
                stage TEXT NOT NULL,
                status TEXT NOT NULL,
                message TEXT NOT NULL,
                created_at REAL NOT NULL
            )
        """)
        conn.execute("CREATE INDEX IF NOT EXISTS idx_job_events_job ON job_events(job_id)")

        # --- Privacy Assessments ---
        conn.execute("""
            CREATE TABLE IF NOT EXISTS privacy_assessments (
                id TEXT PRIMARY KEY,
                job_id TEXT UNIQUE NOT NULL REFERENCES jobs(id) ON DELETE CASCADE,
                dataset_id TEXT REFERENCES datasets(id) ON DELETE SET NULL,
                organisation_id TEXT REFERENCES organisations(id) ON DELETE SET NULL,
                pii_detected INTEGER NOT NULL DEFAULT 0,
                residual_leakage INTEGER NOT NULL DEFAULT 0,
                canary_planted INTEGER NOT NULL DEFAULT 0,
                canary_leaks INTEGER NOT NULL DEFAULT 0,
                canary_status TEXT NOT NULL DEFAULT 'NOT_RUN',
                qi_risk_score REAL NOT NULL DEFAULT 0.0,
                reid_risk_level TEXT NOT NULL DEFAULT 'NOT_MEASURED',
                release_eligible INTEGER NOT NULL DEFAULT 0,
                details_json TEXT,
                created_at REAL NOT NULL
            )
        """)

        # --- Identity Clusters ---
        conn.execute("""
            CREATE TABLE IF NOT EXISTS identity_clusters (
                id TEXT PRIMARY KEY,
                job_id TEXT UNIQUE NOT NULL REFERENCES jobs(id) ON DELETE CASCADE,
                organisation_id TEXT REFERENCES organisations(id) ON DELETE SET NULL,
                precision REAL,
                recall REAL,
                f05 REAL,
                false_merges INTEGER NOT NULL DEFAULT 0,
                total_patients INTEGER NOT NULL DEFAULT 0,
                cross_hospital_links INTEGER NOT NULL DEFAULT 0,
                abstentions INTEGER NOT NULL DEFAULT 0,
                conflicts INTEGER NOT NULL DEFAULT 0,
                graph_json TEXT,
                created_at REAL NOT NULL
            )
        """)

        # --- Clinical Reports ---
        conn.execute("""
            CREATE TABLE IF NOT EXISTS clinical_reports (
                id TEXT PRIMARY KEY,
                job_id TEXT UNIQUE NOT NULL REFERENCES jobs(id) ON DELETE CASCADE,
                organisation_id TEXT REFERENCES organisations(id) ON DELETE SET NULL,
                expected_values INTEGER NOT NULL DEFAULT 0,
                preserved_values INTEGER NOT NULL DEFAULT 0,
                modified_values INTEGER NOT NULL DEFAULT 0,
                missing_values INTEGER NOT NULL DEFAULT 0,
                medication_integrity REAL,
                dosage_integrity REAL,
                lab_integrity REAL,
                vital_integrity REAL,
                fhir_integrity TEXT DEFAULT 'NOT_MEASURED',
                details_json TEXT,
                created_at REAL NOT NULL
            )
        """)

        # --- Attack Runs ---
        conn.execute("""
            CREATE TABLE IF NOT EXISTS attack_runs (
                id TEXT PRIMARY KEY,
                job_id TEXT REFERENCES jobs(id) ON DELETE SET NULL,
                dataset_id TEXT REFERENCES datasets(id) ON DELETE SET NULL,
                organisation_id TEXT REFERENCES organisations(id) ON DELETE SET NULL,
                profile TEXT NOT NULL,
                risk_score REAL NOT NULL DEFAULT 0.0,
                blocked_count INTEGER NOT NULL DEFAULT 0,
                total_count INTEGER NOT NULL DEFAULT 0,
                results_json TEXT,
                created_by TEXT REFERENCES users(id) ON DELETE SET NULL,
                created_at REAL NOT NULL
            )
        """)

        # --- Privacy Passports ---
        conn.execute("""
            CREATE TABLE IF NOT EXISTS passports (
                id TEXT PRIMARY KEY,
                job_id TEXT UNIQUE NOT NULL REFERENCES jobs(id) ON DELETE CASCADE,
                dataset_id TEXT REFERENCES datasets(id) ON DELETE SET NULL,
                organisation_id TEXT REFERENCES organisations(id) ON DELETE SET NULL,
                manifest_hash TEXT NOT NULL,
                signature_status TEXT NOT NULL DEFAULT 'UNSIGNED',
                passport_json TEXT NOT NULL,
                created_by TEXT REFERENCES users(id) ON DELETE SET NULL,
                created_at REAL NOT NULL,
                verified_at REAL
            )
        """)

        # --- Research Requests (preserve & extend) ---
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
        _add_column_if_missing(conn, "research_requests", "organisation_id", "TEXT")
        _add_column_if_missing(conn, "research_requests", "dataset_id", "TEXT")
        _add_column_if_missing(conn, "research_requests", "created_by", "TEXT")
        _add_column_if_missing(conn, "research_requests", "reviewed_by", "TEXT")
        _add_column_if_missing(conn, "research_requests", "reviewed_at", "REAL")

        # --- Legacy audit_logs (keep for compatibility) & new Audit Events ---
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
                details TEXT,
                ip_address TEXT
            )
        """)
        conn.execute("CREATE INDEX IF NOT EXISTS idx_audit_events_ts ON audit_events(timestamp DESC)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_audit_events_org ON audit_events(organisation_id)")

        # --- Settings ---
        conn.execute("""
            CREATE TABLE IF NOT EXISTS settings (
                key TEXT PRIMARY KEY,
                value TEXT
            )
        """)

        # Record migration
        conn.execute(
            "INSERT OR IGNORE INTO schema_migrations (version, applied_at) VALUES (?, ?)",
            ("m17_v1", time.time()),
        )

        # Seed synthetic organisations if empty
        cur = conn.execute("SELECT COUNT(*) as cnt FROM organisations")
        if cur.fetchone()["cnt"] == 0:
            now = time.time()
            orgs = [
                ("org-hosp-a", "Metro General Hospital", "Hospital", "Delhi NCR", "Active", 0, now - 86400 * 30),
                ("org-hosp-b", "Apex Care Medical Centre", "Hospital", "Mumbai", "Active", 0, now - 86400 * 20),
                ("org-lab-c", "ThyroCare Bio Diagnostics", "Diagnostic Lab", "Bengaluru", "Active", 0, now - 86400 * 15),
                ("org-res-d", "National Institute of Epidemiology", "Research Institute", "Chennai", "Active", 0, now - 86400 * 10),
            ]
            conn.executemany(
                "INSERT INTO organisations (id, name, org_type, region, status, records_contributed, joined_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
                orgs,
            )

        # Seed default users + memberships if empty (no passwords; authenticate via Email OTP or Google)
        cur = conn.execute("SELECT COUNT(*) as cnt FROM users")
        if cur.fetchone()["cnt"] == 0:
            now = time.time()
            seed_users = [
                ("usr-admin", "admin@medilocker.local", "Platform Administrator", "ACTIVE", "PLATFORM_ADMIN", now),
                ("usr-privacy", "privacy@metrogeneral.org", "Dr. Priya Nair (Privacy Officer)", "ACTIVE", "USER", now),
                ("usr-research", "research@nie.org", "Dr. Arjun Rao (Researcher)", "ACTIVE", "USER", now),
                ("usr-auditor", "audit@medilocker.local", "Compliance Auditor", "ACTIVE", "USER", now),
            ]
            conn.executemany(
                "INSERT INTO users (id, email, full_name, status, platform_role, created_at) VALUES (?, ?, ?, ?, ?, ?)",
                seed_users,
            )
            seed_memberships = [
                ("mem-1", "usr-admin", "org-hosp-a", "ORG_ADMIN", now),
                ("mem-2", "usr-admin", "org-hosp-b", "ORG_ADMIN", now),
                ("mem-3", "usr-privacy", "org-hosp-a", "PRIVACY_OFFICER", now),
                ("mem-4", "usr-research", "org-res-d", "RESEARCHER", now),
                ("mem-5", "usr-auditor", "org-hosp-a", "AUDITOR", now),
            ]
            conn.executemany(
                "INSERT INTO memberships (id, user_id, organisation_id, role, created_at) VALUES (?, ?, ?, ?, ?)",
                seed_memberships,
            )
