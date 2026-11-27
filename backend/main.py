"""MediLocker Healthcare Privacy Platform Backend API (Milestone 17).
Built with FastAPI.
- Web authentication (SMTP Email OTP + Google OAuth 2.0/OIDC + RBAC) is decoupled
  from the offline privacy engine (starter/main.py).
- All dashboard, privacy, clinical, identity, passport, and audit endpoints are
  backed by real SQLite persistence and real engine execution.
"""
from __future__ import annotations

import hashlib
import html
import io
import json
import os
import re
import secrets
import sys
import time
import zipfile
from pathlib import Path
from typing import Any, Dict, List, Optional

from fastapi import (
    Depends,
    FastAPI,
    File,
    Form,
    HTTPException,
    Query,
    Request,
    Response,
    UploadFile,
    status,
)
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, StreamingResponse
from pydantic import BaseModel

# Load .env from repository root if present (without overriding existing env vars)
_ENV_FILE = Path(__file__).resolve().parent.parent / ".env"
if _ENV_FILE.exists():
    for _line in _ENV_FILE.read_text(encoding="utf-8").splitlines():
        _line = _line.strip()
        if not _line or _line.startswith("#") or "=" not in _line:
            continue
        _k, _v = _line.split("=", 1)
        _k = _k.strip()
        _v = _v.strip().strip('"').strip("'")
        if _k and _k not in os.environ:
            os.environ[_k] = _v

from .audit import record_audit_event
from .dashboard_metrics import (
    get_dashboard_metrics_summary,
    get_runtime_execution_compliance,
)
from .auth import (
    ROLE_AUDITOR,
    ROLE_ORG_ADMIN,
    ROLE_PLATFORM_ADMIN,
    ROLE_PRIVACY_OFFICER,
    ROLE_RESEARCHER,
    clear_session_cookie,
    create_google_auth_url,
    dev_email_login,
    get_google_config,
    get_smtp_config,
    get_operating_mode,
    handle_google_callback,
    is_dev_email_login_enabled,
    is_judge_mode,
    is_offline_mode_enabled,
    offline_demo_login,
    request_email_otp,
    require_org_access,
    require_roles,
    require_user,
    revoke_session_by_token,
    set_session_cookie,
    user_has_org_access,
    verify_email_otp,
)
from .database import get_db, init_db
from .engine_adapter import STARTER_DIR, compute_file_sha256
from .pipeline import (
    DATASETS_DIR,
    JOBS_DIR,
    execute_job_pipeline,
    launch_job_async,
    run_attack_simulation_for_job,
)
from .services.pdf_reporting import (
    PdfGenerationError,
    PdfSecurityError,
    generate_attack_simulation_pdf,
    generate_audit_trail_pdf,
    generate_clinical_integrity_pdf,
    generate_privacy_intelligence_pdf,
    generate_privacy_passport_pdf,
)

init_db()

app = FastAPI(
    title="MediLocker Healthcare Privacy Platform API",
    version="2.0.0",
    description="Integrated API for MediLocker Privacy Infrastructure, Identity Continuity, Clinical Integrity & Audit",
)

allowed_origins = [
    o.strip()
    for o in os.environ.get(
        "FRONTEND_ORIGINS",
        "http://127.0.0.1:3001,http://127.0.0.1:3000,http://localhost:3001,http://localhost:3000",
    ).split(",")
    if o.strip()
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type"],
)

ALLOWED_UPLOAD_EXTENSIONS = {".csv", ".tsv", ".json", ".jsonl", ".txt", ".pdf", ".png"}


def sanitize_filename(name: str) -> str:
    cleaned = re.sub(r"[^a-zA-Z0-9_.-]", "_", Path(name).name)
    if not cleaned or cleaned.startswith("."):
        cleaned = f"file_{int(time.time())}.dat"
    return cleaned


def _client_ip(request: Request) -> str:
    return request.client.host if request.client else "unknown"


def _authorised_org_ids(user: Dict[str, Any]) -> Optional[List[str]]:
    if user.get("platform_role") == ROLE_PLATFORM_ADMIN:
        return None  # unrestricted
    return [m["organisation_id"] for m in user.get("memberships", [])]


def _org_filter_clause(org_ids: Optional[List[str]], column: str = "organisation_id") -> tuple[str, list[Any]]:
    if org_ids is None:
        return "1=1", []
    if not org_ids:
        return "1=0", []
    placeholders = ",".join("?" for _ in org_ids)
    return f"{column} IN ({placeholders})", list(org_ids)


# ==============================================================================
# 1. Health & Authentication (SMTP OTP + Google OAuth 2.0)
# ==============================================================================


@app.get("/api/health")
def get_health() -> Dict[str, Any]:
    return {
        "status": "healthy",
        "platform": "MediLocker",
        "engine": "GuptKavach Offline Privacy Engine",
        "engine_version": "2.0-deterministic",
        "mode": "air-gapped-cpu",
        "timestamp": time.time(),
    }


@app.get("/api/system/diagnostics")
def get_system_diagnostics(user: Dict[str, Any] = Depends(require_user)) -> Dict[str, Any]:
    import shutil
    from .database import get_db_path

    db_path = get_db_path()
    usage = shutil.disk_usage(db_path.parent)
    version_file = Path(__file__).resolve().parent.parent / "VERSION"
    version = version_file.read_text(encoding="utf-8").strip() if version_file.exists() else "2.0.0-desktop"
    return {
        "desktop_runtime": "Electron + Frozen Python" if getattr(sys, "frozen", False) else "Local Python + Node",
        "api_status": "HEALTHY",
        "engine_status": "READY" if (STARTER_DIR / "main.py").exists() else "UNAVAILABLE",
        "database_status": "CONNECTED" if db_path.exists() else "INITIALISED",
        "encryption_configured": bool(os.environ.get("RAKSHA_SECRET")),
        "offline_mode": is_offline_mode_enabled(),
        "disk_free_bytes": usage.free,
        "disk_total_bytes": usage.total,
        "data_dir": str(db_path.parent),
        "version": version,
    }


@app.get("/api/reports/brief-pdf")
def download_brief_pdf(user: Dict[str, Any] = Depends(require_user)):
    from reportlab.lib.pagesizes import A4
    from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer
    from reportlab.lib.styles import getSampleStyleSheet

    reports_dir = Path(os.environ.get("MEDILOCKER_DATA_DIR") or (Path(__file__).resolve().parent.parent / "data")) / "reports"
    reports_dir.mkdir(parents=True, exist_ok=True)
    pdf_path = reports_dir / "MediLocker_Operational_Report.pdf"

    dash = _compute_dashboard_payload(user)
    doc = SimpleDocTemplate(str(pdf_path), pagesize=A4)
    styles = getSampleStyleSheet()
    story = [
        Paragraph("MediLocker Operational Privacy Report", styles["Title"]),
        Spacer(1, 12),
        Paragraph(f"Overall Release Readiness: {dash['privacy_health']['overall_readiness']}", styles["Normal"]),
        Paragraph(f"Files Processed: {dash['metrics']['files_processed']['display']}", styles["Normal"]),
        Paragraph(f"Records Processed: {dash['metrics']['records_processed']['display']}", styles["Normal"]),
        Paragraph(f"PII Detected: {dash['metrics']['pii_detected']['display']}", styles["Normal"]),
        Paragraph(f"Clinical Values Preserved: {dash['metrics']['clinical_preserved']['display']}", styles["Normal"]),
        Paragraph(f"Identity Precision: {dash['metrics']['identity_precision']['display']}", styles["Normal"]),
        Paragraph(f"Canary Leaks: {dash['metrics']['canary_leaks']['display']}", styles["Normal"]),
    ]
    doc.build(story)
    return StreamingResponse(
        io.BytesIO(pdf_path.read_bytes()),
        media_type="application/pdf",
        headers={"Content-Disposition": "attachment; filename=MediLocker_Operational_Report.pdf"},
    )


@app.get("/api/auth/config")
def get_auth_config() -> Dict[str, Any]:
    smtp = get_smtp_config()
    google = get_google_config()
    return {
        "mode": get_operating_mode(),
        "judge_mode": is_judge_mode(),
        "offline_mode": is_offline_mode_enabled(),
        "smtp_enabled": smtp["configured"],
        "dev_email_login_enabled": is_dev_email_login_enabled(),
        "google_enabled": google["configured"],
        "google_client_id": google["client_id"] if google["configured"] else None,
        "google_redirect_uri": google["redirect_uri"] if google["configured"] else None,
    }


class RegisterBody(BaseModel):
    email: str
    full_name: str
    organisation_id: Optional[str] = None


@app.post("/api/auth/register")
def register_user(body: RegisterBody, request: Request) -> Dict[str, Any]:
    email = body.email.strip().lower()
    if not re.match(r"^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$", email):
        raise HTTPException(status_code=400, detail="Invalid email address")
    if not body.full_name.strip():
        raise HTTPException(status_code=400, detail="Full name is required")

    now = time.time()
    with get_db() as conn:
        existing = conn.execute("SELECT id FROM users WHERE lower(email) = ?", (email,)).fetchone()
        if existing:
            # Generic response to prevent account enumeration
            return {
                "status": "ok",
                "message": "If this email is eligible, you can now sign in with Email OTP.",
            }
        user_id = f"usr-{secrets.token_hex(8)}"
        conn.execute(
            "INSERT INTO users (id, email, full_name, status, platform_role, created_at) VALUES (?, ?, ?, 'ACTIVE', 'USER', ?)",
            (user_id, email, body.full_name.strip(), now),
        )
        # Assign default researcher membership on requested org (if exists) or first org
        org_row = None
        if body.organisation_id:
            org_row = conn.execute("SELECT id FROM organisations WHERE id = ?", (body.organisation_id,)).fetchone()
        if not org_row:
            org_row = conn.execute("SELECT id FROM organisations ORDER BY joined_at ASC LIMIT 1").fetchone()
        if org_row:
            conn.execute(
                "INSERT INTO memberships (id, user_id, organisation_id, role, created_at) VALUES (?, ?, ?, ?, ?)",
                (f"mem-{secrets.token_hex(8)}", user_id, org_row["id"], ROLE_RESEARCHER, now),
            )

    record_audit_event(
        action="USER_REGISTERED",
        resource_type="user",
        resource_id=user_id,
        outcome="SUCCESS",
        actor_id=user_id,
        actor_email=email,
        details="Registered new account",
        ip_address=_client_ip(request),
    )
    return {
        "status": "ok",
        "message": "If this email is eligible, you can now sign in with Email OTP.",
    }


class OtpRequestBody(BaseModel):
    email: str
    purpose: str = "login"


@app.post("/api/auth/otp/request")
def auth_otp_request(body: OtpRequestBody, request: Request) -> Dict[str, Any]:
    return request_email_otp(body.email, body.purpose, _client_ip(request))


class OtpVerifyBody(BaseModel):
    email: str
    code: str
    purpose: str = "login"


class DevLoginBody(BaseModel):
    email: str


class OfflineDemoBody(BaseModel):
    email: Optional[str] = None


@app.post("/api/auth/offline-demo")
def auth_offline_demo(
    request: Request,
    response: Response,
    body: Optional[OfflineDemoBody] = None,
) -> Dict[str, Any]:
    raw_token, ctx = offline_demo_login(
        body.email if body else None,
        _client_ip(request),
        request.headers.get("user-agent"),
    )
    set_session_cookie(response, raw_token)
    return {"user": ctx, "token": raw_token}


@app.post("/api/auth/dev-login")
def auth_dev_login(body: DevLoginBody, request: Request, response: Response) -> Dict[str, Any]:
    raw_token, ctx = dev_email_login(
        body.email,
        _client_ip(request),
        request.headers.get("user-agent"),
    )
    set_session_cookie(response, raw_token)
    return {"user": ctx, "token": raw_token}


@app.post("/api/auth/otp/verify")
def auth_otp_verify(body: OtpVerifyBody, request: Request, response: Response) -> Dict[str, Any]:
    raw_token, ctx = verify_email_otp(
        body.email,
        body.code,
        body.purpose,
        _client_ip(request),
        request.headers.get("user-agent"),
    )
    set_session_cookie(response, raw_token)
    return {"user": ctx, "token": raw_token}


@app.get("/api/auth/google/login")
def auth_google_login(
    link_account: bool = False,
    request: Request = None,  # type: ignore
) -> Dict[str, str]:
    link_user_id = None
    if link_account:
        from .auth import get_current_user_optional

        # Require existing authenticated session to link Google account
        raise HTTPException(status_code=400, detail="Use /api/auth/google/link while authenticated")
    return create_google_auth_url(link_user_id=link_user_id)


@app.post("/api/auth/google/link")
def auth_google_link(user: Dict[str, Any] = Depends(require_user)) -> Dict[str, str]:
    return create_google_auth_url(link_user_id=user["id"])


class GoogleCallbackBody(BaseModel):
    code: str
    state: str


@app.post("/api/auth/google/callback")
def auth_google_callback_post(
    body: GoogleCallbackBody, request: Request, response: Response
) -> Dict[str, Any]:
    raw_token, ctx = handle_google_callback(
        body.code,
        body.state,
        _client_ip(request),
        request.headers.get("user-agent"),
    )
    set_session_cookie(response, raw_token)
    return {"user": ctx, "token": raw_token}


@app.get("/api/auth/google/callback")
def auth_google_callback_get(
    code: str, state: str, request: Request, response: Response
) -> Dict[str, Any]:
    raw_token, ctx = handle_google_callback(
        code,
        state,
        _client_ip(request),
        request.headers.get("user-agent"),
    )
    set_session_cookie(response, raw_token)
    return {"user": ctx, "token": raw_token}


@app.get("/api/auth/me")
def auth_me(user: Dict[str, Any] = Depends(require_user)) -> Dict[str, Any]:
    safe_user = {k: v for k, v in user.items() if k != "raw_token"}
    return {"user": safe_user}


class SwitchOrgBody(BaseModel):
    organisation_id: str


@app.post("/api/auth/switch-org")
def auth_switch_org(body: SwitchOrgBody, user: Dict[str, Any] = Depends(require_user)) -> Dict[str, Any]:
    require_org_access(user, body.organisation_id)
    with get_db() as conn:
        conn.execute(
            "UPDATE sessions SET active_org_id = ? WHERE id = ?",
            (body.organisation_id, user["session_id"]),
        )
    return {"status": "ok", "active_org_id": body.organisation_id}


@app.post("/api/auth/logout")
def auth_logout(
    request: Request, response: Response, user: Dict[str, Any] = Depends(require_user)
) -> Dict[str, str]:
    raw_token = user.get("raw_token")
    if raw_token:
        revoke_session_by_token(raw_token)
    clear_session_cookie(response)
    record_audit_event(
        action="LOGOUT",
        resource_type="session",
        resource_id=user.get("session_id"),
        outcome="SUCCESS",
        actor_id=user["id"],
        actor_email=user["email"],
        actor_role=user.get("active_role"),
        organisation_id=user.get("active_org_id"),
        ip_address=_client_ip(request),
    )
    return {"status": "ok"}


# ==============================================================================
# 2. Dashboard (Real Persistent Metrics + Strict Empty States)
# ==============================================================================


def _compute_dashboard_payload(user: Dict[str, Any]) -> Dict[str, Any]:
    org_ids = _authorised_org_ids(user)
    where_org, org_params = _org_filter_clause(org_ids, "organisation_id")

    with get_db() as conn:
        datasets_count = conn.execute(
            f"SELECT COUNT(*) as c FROM datasets WHERE deleted_at IS NULL AND {where_org}",
            org_params,
        ).fetchone()["c"]

        jobs_rows = [
            dict(r)
            for r in conn.execute(
                f"""
                SELECT j.*, d.name as dataset_name, o.name as organisation_name
                FROM jobs j
                LEFT JOIN datasets d ON d.id = j.dataset_id
                LEFT JOIN organisations o ON o.id = j.organisation_id
                WHERE {where_org.replace('organisation_id', 'j.organisation_id')}
                ORDER BY j.created_at DESC
                """,
                org_params,
            ).fetchall()
        ]

        assessments = [
            dict(r)
            for r in conn.execute(
                f"SELECT * FROM privacy_assessments WHERE {where_org} ORDER BY created_at DESC",
                org_params,
            ).fetchall()
        ]

        clinical_rows = [
            dict(r)
            for r in conn.execute(
                f"SELECT * FROM clinical_reports WHERE {where_org} ORDER BY created_at DESC",
                org_params,
            ).fetchall()
        ]

        identity_rows = [
            dict(r)
            for r in conn.execute(
                f"SELECT * FROM identity_clusters WHERE {where_org} ORDER BY created_at DESC",
                org_params,
            ).fetchall()
        ]

        audit_rows = [
            dict(r)
            for r in conn.execute(
                f"SELECT * FROM audit_events WHERE ({where_org} OR organisation_id IS NULL) ORDER BY timestamp DESC LIMIT 8",
                org_params,
            ).fetchall()
        ]

    completed_jobs = [
        j for j in jobs_rows if j["status"] in ("COMPLETED", "COMPLETED_WITH_WARNINGS", "QUARANTINED", "BLOCKED")
    ]
    files_processed = sum(int(j.get("files_total") or 0) for j in completed_jobs)
    files_sanitized = sum(int(j.get("files_sanitized") or 0) for j in completed_jobs)
    files_quarantined = sum(int(j.get("files_quarantined") or 0) for j in completed_jobs)
    records_processed = sum(int(j.get("records_processed") or 0) for j in completed_jobs)

    # PII Detected
    if assessments:
        total_pii = sum(int(a["pii_detected"]) for a in assessments)
        total_leaks = sum(int(a["residual_leakage"]) for a in assessments)
        pii_metric = {
            "value": total_pii,
            "display": str(total_pii),
            "status": "PASS" if total_leaks == 0 else "FAILED",
            "description": f"{total_leaks} residual leaks across {len(assessments)} assessment(s)",
        }
    else:
        pii_metric = {
            "value": None,
            "display": "Not measured",
            "status": "NOT_MEASURED",
            "description": "No privacy assessments executed yet",
        }

    # Clinical Values Preserved
    total_exp = sum(int(c["expected_values"]) for c in clinical_rows)
    total_pres = sum(int(c["preserved_values"]) for c in clinical_rows)
    if clinical_rows and total_exp > 0:
        clin_status = "PASS" if total_pres == total_exp else "WARNING"
        clinical_metric = {
            "value": total_pres,
            "expected": total_exp,
            "display": f"{total_pres}/{total_exp}",
            "status": clin_status,
            "description": f"{round((total_pres / total_exp) * 100, 1)}% clinical items preserved",
        }
    else:
        clinical_metric = {
            "value": None,
            "expected": None,
            "display": "Not measured",
            "status": "NOT_MEASURED",
            "description": "No clinical validation reports measured yet",
        }

    # Identity Precision
    eval_id = [i for i in identity_rows if i["precision"] is not None]
    if eval_id:
        latest_id = eval_id[0]
        false_merges = sum(int(i["false_merges"]) for i in eval_id)
        id_metric = {
            "value": latest_id["precision"],
            "display": f"{latest_id['precision']:.2f}",
            "status": "PASS" if false_merges == 0 else "FAILED",
            "description": f"{false_merges} false merges across {len(eval_id)} evaluation(s)",
        }
    else:
        id_metric = {
            "value": None,
            "display": "Not measured",
            "status": "NOT_MEASURED",
            "description": "No identity evaluations executed yet",
        }

    # Canary Leaks
    canary_tested = [a for a in assessments if a["canary_status"] != "NOT_RUN"]
    if canary_tested:
        planted = sum(int(a["canary_planted"]) for a in canary_tested)
        leaked = sum(int(a["canary_leaks"]) for a in canary_tested)
        canary_metric = {
            "value": leaked,
            "planted": planted,
            "display": f"{leaked}/{planted}",
            "status": "PASS" if leaked == 0 else "FAILED",
            "description": "All canary tracers contained" if leaked == 0 else "Canary leak detected!",
        }
    else:
        canary_metric = {
            "value": None,
            "planted": 0,
            "display": "Not tested",
            "status": "NOT_RUN",
            "description": "No canary test dataset executed yet",
        }

    # Overall Release Readiness
    latest_job = jobs_rows[0] if jobs_rows else None
    critical_risks = sum(1 for a in assessments if a["canary_leaks"] > 0 or a["reid_risk_level"] == "CRITICAL")
    pending_jobs = sum(1 for j in jobs_rows if j["status"] in ("CREATED", "VALIDATING", "QUEUED", "PROCESSING", "PRIVACY_ANALYSIS", "CLINICAL_VALIDATION", "SECURITY_VALIDATION"))
    verified_jobs = [j for j in jobs_rows if j["release_decision"] == "APPROVED"]

    if not jobs_rows:
        overall_readiness = "NOT_RUN"
    elif critical_risks > 0 or (latest_job and latest_job["status"] in ("BLOCKED", "FAILED")):
        overall_readiness = "BLOCKED"
    elif latest_job and latest_job["status"] in ("QUARANTINED", "COMPLETED_WITH_WARNINGS"):
        overall_readiness = "WARNING"
    elif pending_jobs > 0:
        overall_readiness = "WARNING"
    else:
        overall_readiness = "PASS"

    return {
        "metrics": {
            "files_processed": {
                "value": files_processed,
                "display": str(files_processed),
                "status": "PASS" if files_processed > 0 else "NOT_RUN",
                "description": f"{files_sanitized} sanitised · {files_quarantined} quarantined" if files_processed > 0 else "No files processed yet",
                "scope": f"{datasets_count} dataset(s)",
            },
            "records_processed": {
                "value": records_processed,
                "display": str(records_processed),
                "status": "PASS" if records_processed > 0 else "NOT_RUN",
                "description": "Total patient records processed" if records_processed > 0 else "No records processed yet",
                "scope": "Persistent DB",
            },
            "pii_detected": pii_metric,
            "clinical_preserved": clinical_metric,
            "identity_precision": id_metric,
            "canary_leaks": canary_metric,
        },
        "privacy_health": {
            "overall_readiness": overall_readiness,
            "latest_job_id": latest_job["id"] if latest_job else None,
            "latest_job_status": latest_job["status"] if latest_job else "NOT_RUN",
            "critical_unresolved_risks": critical_risks,
            "pending_checks": pending_jobs,
            "latest_verified_at": verified_jobs[0]["completed_at"] if verified_jobs else None,
        },
        "recent_jobs": jobs_rows[:10],
        "audit_events": audit_rows,
        "freshness": time.time(),
    }


@app.get("/api/dashboard")
@app.get("/api/dashboard/overview")
def get_dashboard_overview(user: Dict[str, Any] = Depends(require_user)) -> Dict[str, Any]:
    return _compute_dashboard_payload(user)


@app.get("/api/dashboard/metrics")
def get_dashboard_metrics(user: Dict[str, Any] = Depends(require_user)) -> Dict[str, Any]:
    return _compute_dashboard_payload(user)["metrics"]


@app.get("/api/dashboard/recent-jobs")
def get_dashboard_recent_jobs(user: Dict[str, Any] = Depends(require_user)) -> List[Dict[str, Any]]:
    return _compute_dashboard_payload(user)["recent_jobs"]


@app.get("/api/dashboard/audit-events")
def get_dashboard_audit_events(user: Dict[str, Any] = Depends(require_user)) -> List[Dict[str, Any]]:
    return _compute_dashboard_payload(user)["audit_events"]


@app.get("/api/system/compliance")
def get_system_compliance() -> Dict[str, Any]:
    """Publicly safe repository/runtime execution compliance check (zero patient or org data)."""
    return get_runtime_execution_compliance()


@app.get("/api/dashboard/metrics-summary")
def get_dashboard_metrics_summary_endpoint(
    scope: str = Query(default="latest"),
    user: Dict[str, Any] = Depends(require_user),
) -> Dict[str, Any]:
    org_ids = _authorised_org_ids(user)
    with get_db() as conn:
        try:
            return get_dashboard_metrics_summary(conn, org_ids, scope=scope)
        except PermissionError as exc:
            raise HTTPException(status_code=403, detail=str(exc))
        except LookupError as exc:
            raise HTTPException(status_code=404, detail=str(exc))


@app.get("/api/jobs/{job_id}/dashboard-metrics")
def get_job_dashboard_metrics_endpoint(
    job_id: str,
    user: Dict[str, Any] = Depends(require_user),
) -> Dict[str, Any]:
    org_ids = _authorised_org_ids(user)
    with get_db() as conn:
        try:
            return get_dashboard_metrics_summary(conn, org_ids, scope=job_id)
        except PermissionError as exc:
            raise HTTPException(status_code=403, detail=str(exc))
        except LookupError as exc:
            raise HTTPException(status_code=404, detail=str(exc))


# ==============================================================================
# 3. Organisations & Members
# ==============================================================================


@app.get("/api/organisations")
def list_organisations(user: Dict[str, Any] = Depends(require_user)) -> List[Dict[str, Any]]:
    org_ids = _authorised_org_ids(user)
    where_org, params = _org_filter_clause(org_ids, "id")
    with get_db() as conn:
        rows = conn.execute(
            f"SELECT * FROM organisations WHERE {where_org} ORDER BY joined_at ASC", params
        ).fetchall()
    return [dict(r) for r in rows]


class CreateOrgBody(BaseModel):
    name: str
    org_type: str
    region: str = "India"


@app.post("/api/organisations")
def create_organisation(
    body: CreateOrgBody,
    request: Request,
    user: Dict[str, Any] = Depends(require_roles([ROLE_PLATFORM_ADMIN])),
) -> Dict[str, Any]:
    org_id = f"org-{secrets.token_hex(6)}"
    now = time.time()
    with get_db() as conn:
        conn.execute(
            "INSERT INTO organisations (id, name, org_type, region, status, records_contributed, joined_at) VALUES (?, ?, ?, ?, 'Active', 0, ?)",
            (org_id, body.name.strip(), body.org_type.strip(), body.region.strip(), now),
        )
        row = dict(conn.execute("SELECT * FROM organisations WHERE id = ?", (org_id,)).fetchone())
    record_audit_event(
        action="ORGANISATION_CREATED",
        resource_type="organisation",
        resource_id=org_id,
        outcome="SUCCESS",
        actor_id=user["id"],
        actor_email=user["email"],
        actor_role=user.get("active_role"),
        organisation_id=org_id,
        ip_address=_client_ip(request),
    )
    return row


@app.get("/api/organisations/{org_id}")
def get_organisation(org_id: str, user: Dict[str, Any] = Depends(require_user)) -> Dict[str, Any]:
    require_org_access(user, org_id)
    with get_db() as conn:
        row = conn.execute("SELECT * FROM organisations WHERE id = ?", (org_id,)).fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Organisation not found")
        datasets = [
            dict(r)
            for r in conn.execute(
                "SELECT id, name, format, file_count, status, created_at FROM datasets WHERE organisation_id = ? AND deleted_at IS NULL",
                (org_id,),
            ).fetchall()
        ]
    out = dict(row)
    out["datasets"] = datasets
    return out


@app.get("/api/organisations/{org_id}/members")
def get_organisation_members(org_id: str, user: Dict[str, Any] = Depends(require_user)) -> List[Dict[str, Any]]:
    require_org_access(user, org_id)
    with get_db() as conn:
        rows = conn.execute(
            """
            SELECT m.id, m.user_id, m.role, m.created_at, u.email, u.full_name, u.status
            FROM memberships m
            JOIN users u ON u.id = m.user_id
            WHERE m.organisation_id = ?
            ORDER BY m.created_at ASC
            """,
            (org_id,),
        ).fetchall()
    return [dict(r) for r in rows]


# ==============================================================================
# 4. Datasets & Processing Jobs
# ==============================================================================


@app.get("/api/datasets")
def list_datasets(user: Dict[str, Any] = Depends(require_user)) -> List[Dict[str, Any]]:
    org_ids = _authorised_org_ids(user)
    where_org, params = _org_filter_clause(org_ids, "d.organisation_id")
    with get_db() as conn:
        rows = conn.execute(
            f"""
            SELECT d.*, o.name as organisation_name,
                   (SELECT j.id FROM jobs j WHERE j.dataset_id = d.id ORDER BY j.created_at DESC LIMIT 1) as latest_job_id,
                   (SELECT j.status FROM jobs j WHERE j.dataset_id = d.id ORDER BY j.created_at DESC LIMIT 1) as latest_job_status,
                   (SELECT j.release_decision FROM jobs j WHERE j.dataset_id = d.id ORDER BY j.created_at DESC LIMIT 1) as latest_release_decision,
                   (SELECT j.records_processed FROM jobs j WHERE j.dataset_id = d.id ORDER BY j.created_at DESC LIMIT 1) as records
            FROM datasets d
            JOIN organisations o ON o.id = d.organisation_id
            WHERE d.deleted_at IS NULL AND {where_org}
            ORDER BY d.created_at DESC
            """,
            params,
        ).fetchall()
    return [dict(r) for r in rows]


@app.post("/api/datasets")
async def upload_dataset(
    request: Request,
    organisation_id: Optional[str] = Form(None),
    name: Optional[str] = Form(None),
    description: str = Form(""),
    auto_process: bool = Form(True),
    sync: bool = Form(False),
    files: List[UploadFile] = File(...),
    user: Dict[str, Any] = Depends(require_user),
) -> Dict[str, Any]:
    target_org = organisation_id or user.get("active_org_id")
    if not target_org:
        raise HTTPException(status_code=400, detail="No organisation specified")
    require_org_access(user, target_org, [ROLE_PLATFORM_ADMIN, ROLE_ORG_ADMIN, ROLE_PRIVACY_OFFICER])

    if not files or not files[0].filename:
        raise HTTPException(status_code=400, detail="At least one file is required")

    dataset_id = f"ds-{int(time.time())}-{secrets.token_hex(4)}"
    ds_dir = DATASETS_DIR / dataset_id
    ds_dir.mkdir(parents=True, exist_ok=True)

    total_bytes = 0
    formats: set[str] = set()
    hasher = hashlib.sha256()

    for f in files:
        if not f.filename:
            continue
        ext = Path(f.filename).suffix.lower()
        if ext not in ALLOWED_UPLOAD_EXTENSIONS:
            raise HTTPException(status_code=400, detail=f"Unsupported file format: {ext or 'unknown'}")
        safe_name = sanitize_filename(f.filename)
        content = await f.read()
        if len(content) == 0:
            raise HTTPException(status_code=400, detail=f"Empty file is not allowed: {safe_name}")
        (ds_dir / safe_name).write_bytes(content)
        total_bytes += len(content)
        formats.add(ext.lstrip(".").upper())
        hasher.update(content)

    ds_name = (name or "").strip() or (files[0].filename if len(files) == 1 else f"Batch ({len(files)} files)")
    ds_sha256 = hasher.hexdigest()
    now = time.time()

    with get_db() as conn:
        conn.execute(
            """
            INSERT INTO datasets (
                id, organisation_id, name, description, format, file_count,
                total_bytes, sha256, storage_path, status, created_by, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 'VALIDATED', ?, ?)
            """,
            (
                dataset_id,
                target_org,
                ds_name,
                description,
                ",".join(sorted(formats)) or "UNKNOWN",
                len(files),
                total_bytes,
                ds_sha256,
                str(ds_dir),
                user["id"],
                now,
            ),
        )

    record_audit_event(
        action="DATASET_UPLOADED",
        resource_type="dataset",
        resource_id=dataset_id,
        outcome="SUCCESS",
        actor_id=user["id"],
        actor_email=user["email"],
        actor_role=user.get("active_role"),
        organisation_id=target_org,
        details=f"Uploaded {len(files)} file(s), {total_bytes} bytes",
        ip_address=_client_ip(request),
    )

    job = None
    if auto_process:
        job = _create_and_start_job(
            dataset_id=dataset_id,
            organisation_id=target_org,
            input_dir=ds_dir,
            input_name=ds_name,
            user=user,
            sync=sync,
            ip_address=_client_ip(request),
        )

    return {"dataset_id": dataset_id, "job": job}


@app.get("/api/datasets/{dataset_id}")
def get_dataset(dataset_id: str, user: Dict[str, Any] = Depends(require_user)) -> Dict[str, Any]:
    with get_db() as conn:
        row = conn.execute(
            "SELECT * FROM datasets WHERE id = ? AND deleted_at IS NULL", (dataset_id,)
        ).fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Dataset not found")
        ds = dict(row)
        require_org_access(user, ds["organisation_id"])
        jobs = [
            dict(j)
            for j in conn.execute(
                "SELECT * FROM jobs WHERE dataset_id = ? ORDER BY created_at DESC", (dataset_id,)
            ).fetchall()
        ]
    ds["jobs"] = jobs
    return ds


@app.delete("/api/datasets/{dataset_id}")
def delete_dataset(
    dataset_id: str, request: Request, user: Dict[str, Any] = Depends(require_user)
) -> Dict[str, str]:
    with get_db() as conn:
        row = conn.execute(
            "SELECT * FROM datasets WHERE id = ? AND deleted_at IS NULL", (dataset_id,)
        ).fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Dataset not found")
        require_org_access(user, row["organisation_id"], [ROLE_PLATFORM_ADMIN, ROLE_ORG_ADMIN, ROLE_PRIVACY_OFFICER])
        conn.execute("UPDATE datasets SET deleted_at = ?, status = 'DELETED' WHERE id = ?", (time.time(), dataset_id))
    record_audit_event(
        action="DATASET_DELETED",
        resource_type="dataset",
        resource_id=dataset_id,
        outcome="SUCCESS",
        actor_id=user["id"],
        actor_email=user["email"],
        actor_role=user.get("active_role"),
        organisation_id=row["organisation_id"],
        ip_address=_client_ip(request),
    )
    return {"status": "deleted"}


def _create_and_start_job(
    *,
    dataset_id: str,
    organisation_id: str,
    input_dir: Path,
    input_name: str,
    user: Dict[str, Any],
    sync: bool = False,
    idempotency_key: Optional[str] = None,
    ip_address: Optional[str] = None,
) -> Dict[str, Any]:
    if idempotency_key:
        with get_db() as conn:
            existing = conn.execute(
                "SELECT * FROM jobs WHERE idempotency_key = ? AND organisation_id = ?",
                (idempotency_key, organisation_id),
            ).fetchone()
            if existing:
                return dict(existing)

    job_id = f"job-{int(time.time())}-{secrets.token_hex(4)}"
    now = time.time()
    with get_db() as conn:
        conn.execute(
            """
            INSERT INTO jobs (
                id, created_at, status, current_stage, input_name, dataset_id,
                organisation_id, created_by, release_decision, policy_version, idempotency_key
            ) VALUES (?, ?, 'CREATED', 'CREATED', ?, ?, ?, ?, 'PENDING', '2.0-deterministic', ?)
            """,
            (job_id, now, input_name, dataset_id, organisation_id, user["id"], idempotency_key),
        )
        conn.execute(
            "INSERT INTO job_events (job_id, stage, status, message, created_at) VALUES (?, 'CREATED', 'CREATED', 'Processing job created.', ?)",
            (job_id, now),
        )

    record_audit_event(
        action="JOB_CREATED",
        resource_type="job",
        resource_id=job_id,
        outcome="SUCCESS",
        actor_id=user["id"],
        actor_email=user["email"],
        actor_role=user.get("active_role"),
        organisation_id=organisation_id,
        details=f"Created processing job for dataset {dataset_id}",
        ip_address=ip_address,
    )

    kwargs = {
        "job_id": job_id,
        "dataset_id": dataset_id,
        "organisation_id": organisation_id,
        "input_dir": input_dir,
        "actor_id": user["id"],
        "actor_email": user["email"],
        "actor_role": user.get("active_role"),
    }
    if sync:
        execute_job_pipeline(**kwargs)
    else:
        launch_job_async(**kwargs)

    with get_db() as conn:
        return dict(conn.execute("SELECT * FROM jobs WHERE id = ?", (job_id,)).fetchone())


class CreateJobBody(BaseModel):
    dataset_id: str
    sync: bool = False
    idempotency_key: Optional[str] = None


@app.post("/api/jobs")
async def create_job(
    request: Request,
    user: Dict[str, Any] = Depends(require_user),
    dataset_id: Optional[str] = Form(None),
    organisation_id: Optional[str] = Form(None),
    sync: bool = Form(False),
    files: Optional[List[UploadFile]] = File(None),
) -> Dict[str, Any]:
    # Support both JSON body (for existing dataset_id) and multipart upload
    content_type = request.headers.get("content-type", "")
    if "application/json" in content_type:
        body = await request.json()
        ds_id = body.get("dataset_id")
        sync_flag = bool(body.get("sync", False))
        idem_key = body.get("idempotency_key")
        if not ds_id:
            raise HTTPException(status_code=400, detail="dataset_id is required")
        with get_db() as conn:
            ds = conn.execute(
                "SELECT * FROM datasets WHERE id = ? AND deleted_at IS NULL", (ds_id,)
            ).fetchone()
            if not ds:
                raise HTTPException(status_code=404, detail="Dataset not found")
        require_org_access(user, ds["organisation_id"], [ROLE_PLATFORM_ADMIN, ROLE_ORG_ADMIN, ROLE_PRIVACY_OFFICER])
        return _create_and_start_job(
            dataset_id=ds["id"],
            organisation_id=ds["organisation_id"],
            input_dir=Path(ds["storage_path"]),
            input_name=ds["name"],
            user=user,
            sync=sync_flag,
            idempotency_key=idem_key,
            ip_address=_client_ip(request),
        )

    # Multipart upload fallback (compatible with Datasets page upload)
    if files and len(files) > 0 and files[0].filename:
        res = await upload_dataset(
            request=request,
            organisation_id=organisation_id,
            name=None,
            description="",
            auto_process=True,
            sync=sync,
            files=files,
            user=user,
        )
        return res["job"]

    if dataset_id:
        with get_db() as conn:
            ds = conn.execute(
                "SELECT * FROM datasets WHERE id = ? AND deleted_at IS NULL", (dataset_id,)
            ).fetchone()
            if not ds:
                raise HTTPException(status_code=404, detail="Dataset not found")
        require_org_access(user, ds["organisation_id"], [ROLE_PLATFORM_ADMIN, ROLE_ORG_ADMIN, ROLE_PRIVACY_OFFICER])
        return _create_and_start_job(
            dataset_id=ds["id"],
            organisation_id=ds["organisation_id"],
            input_dir=Path(ds["storage_path"]),
            input_name=ds["name"],
            user=user,
            sync=sync,
            ip_address=_client_ip(request),
        )

    raise HTTPException(status_code=400, detail="Provide files or a valid dataset_id")


@app.get("/api/jobs")
def list_jobs(user: Dict[str, Any] = Depends(require_user)) -> List[Dict[str, Any]]:
    org_ids = _authorised_org_ids(user)
    where_org, params = _org_filter_clause(org_ids, "j.organisation_id")
    with get_db() as conn:
        rows = conn.execute(
            f"""
            SELECT j.*, d.name as dataset_name, o.name as organisation_name
            FROM jobs j
            LEFT JOIN datasets d ON d.id = j.dataset_id
            LEFT JOIN organisations o ON o.id = j.organisation_id
            WHERE {where_org}
            ORDER BY j.created_at DESC
            """,
            params,
        ).fetchall()
    return [dict(r) for r in rows]


@app.get("/api/jobs/{job_id}")
def get_job_detail(job_id: str, user: Dict[str, Any] = Depends(require_user)) -> Dict[str, Any]:
    with get_db() as conn:
        row = conn.execute("SELECT * FROM jobs WHERE id = ?", (job_id,)).fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Job not found")
        job = dict(row)
        if job.get("organisation_id"):
            require_org_access(user, job["organisation_id"])
        events = [
            dict(e)
            for e in conn.execute(
                "SELECT * FROM job_events WHERE job_id = ? ORDER BY id ASC", (job_id,)
            ).fetchall()
        ]
    job["events"] = events
    return job


@app.get("/api/jobs/{job_id}/events")
def get_job_events(job_id: str, user: Dict[str, Any] = Depends(require_user)) -> List[Dict[str, Any]]:
    job = get_job_detail(job_id, user)
    return job["events"]


@app.get("/api/jobs/{job_id}/results")
def get_job_results(job_id: str, user: Dict[str, Any] = Depends(require_user)) -> Dict[str, Any]:
    job = get_job_detail(job_id, user)
    with get_db() as conn:
        privacy = conn.execute("SELECT * FROM privacy_assessments WHERE job_id = ?", (job_id,)).fetchone()
        clinical = conn.execute("SELECT * FROM clinical_reports WHERE job_id = ?", (job_id,)).fetchone()
        identity = conn.execute("SELECT * FROM identity_clusters WHERE job_id = ?", (job_id,)).fetchone()
        passport = conn.execute("SELECT * FROM passports WHERE job_id = ?", (job_id,)).fetchone()
    return {
        "job": job,
        "privacy_assessment": dict(privacy) if privacy else None,
        "clinical_report": dict(clinical) if clinical else None,
        "identity_cluster": dict(identity) if identity else None,
        "passport": dict(passport) if passport else None,
    }


@app.get("/api/jobs/{job_id}/download")
def download_job_outputs(
    job_id: str,
    request: Request,
    include_mapping: bool = False,
    user: Dict[str, Any] = Depends(require_user),
):
    job = get_job_detail(job_id, user)
    if job.get("organisation_id"):
        if include_mapping:
            if is_judge_mode():
                raise HTTPException(
                    status_code=403,
                    detail="Restricted patient mapping file download is disabled in Local Evaluation Mode.",
                )
            require_org_access(
                user,
                job["organisation_id"],
                [ROLE_PLATFORM_ADMIN, ROLE_ORG_ADMIN, ROLE_PRIVACY_OFFICER],
            )
        else:
            require_org_access(user, job["organisation_id"])
    if job.get("release_decision") not in ("APPROVED", "APPROVED_WITH_WARNINGS") or job.get("status") not in ("COMPLETED", "COMPLETED_WITH_WARNINGS"):
        raise HTTPException(
            status_code=403,
            detail=f"Bundle download blocked: job status is {job.get('status')} (decision: {job.get('release_decision')})",
        )
    job_output = JOBS_DIR / job_id / "output"
    sanitized_dir = job_output / "sanitized"
    if not sanitized_dir.exists() or not (job_output / "report.json").exists() or not (job_output / "records.jsonl").exists():
        raise HTTPException(status_code=404, detail="Complete sanitized output bundle not found for this job")

    zip_buffer = io.BytesIO()
    with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zf:
        for root, _, files in os.walk(str(sanitized_dir)):
            for f in files:
                file_path = Path(root) / f
                arcname = file_path.relative_to(sanitized_dir).as_posix()
                zf.write(file_path, f"sanitized/{arcname}")
        zf.write(job_output / "report.json", "report.json")
        if (job_output / "privacy_passport.json").is_file():
            zf.write(job_output / "privacy_passport.json", "privacy_passport.json")
        if include_mapping:
            zf.write(job_output / "records.jsonl", "records.jsonl")

    record_audit_event(
        action="BUNDLE_DOWNLOADED",
        resource_type="job",
        resource_id=job_id,
        outcome="SUCCESS",
        actor_id=user["id"],
        actor_email=user["email"],
        actor_role=user.get("active_role"),
        organisation_id=job.get("organisation_id"),
        details=f"Downloaded release bundle ({job.get('release_decision')}, include_mapping={include_mapping})",
        ip_address=_client_ip(request),
    )

    zip_buffer.seek(0)
    return StreamingResponse(
        zip_buffer,
        media_type="application/zip",
        headers={"Content-Disposition": f"attachment; filename=MediLocker_Protected_{job_id}.zip"},
    )


@app.get("/api/jobs/{job_id}/report.json")
def download_job_report_json(
    job_id: str, request: Request, user: Dict[str, Any] = Depends(require_user)
):
    job = get_job_detail(job_id, user)
    if job.get("organisation_id"):
        require_org_access(user, job["organisation_id"])
    report_path = JOBS_DIR / job_id / "output" / "report.json"
    if not report_path.is_file():
        raise HTTPException(status_code=404, detail="Processing report.json not found for this job")
    return StreamingResponse(
        io.BytesIO(report_path.read_bytes()),
        media_type="application/json",
        headers={"Content-Disposition": f"attachment; filename=MediLocker_Report_{job_id}.json"},
    )


@app.get("/api/jobs/{job_id}/mapping")
def download_job_mapping_jsonl(
    job_id: str, request: Request, user: Dict[str, Any] = Depends(require_user)
):
    """Restricted download of sensitive records.jsonl patient mapping file."""
    if is_judge_mode():
        raise HTTPException(
            status_code=403,
            detail="Restricted patient mapping file download is disabled in Local Evaluation Mode.",
        )
    job = get_job_detail(job_id, user)
    if job.get("organisation_id"):
        require_org_access(
            user,
            job["organisation_id"],
            [ROLE_PLATFORM_ADMIN, ROLE_ORG_ADMIN, ROLE_PRIVACY_OFFICER],
        )
    if job.get("release_decision") not in ("APPROVED", "APPROVED_WITH_WARNINGS") or job.get("status") not in ("COMPLETED", "COMPLETED_WITH_WARNINGS"):
        raise HTTPException(
            status_code=403,
            detail=f"Mapping download blocked: job status is {job.get('status')} (decision: {job.get('release_decision')})",
        )
    mapping_path = JOBS_DIR / job_id / "output" / "records.jsonl"
    if not mapping_path.is_file():
        raise HTTPException(status_code=404, detail="Mapping file records.jsonl not found for this job")

    record_audit_event(
        action="MAPPING_DOWNLOADED",
        resource_type="job",
        resource_id=job_id,
        outcome="SUCCESS",
        actor_id=user["id"],
        actor_email=user["email"],
        actor_role=user.get("active_role"),
        organisation_id=job.get("organisation_id"),
        details=f"Downloaded restricted records.jsonl mapping for job {job_id}",
        ip_address=_client_ip(request),
    )
    return StreamingResponse(
        io.BytesIO(mapping_path.read_bytes()),
        media_type="application/x-ndjson",
        headers={"Content-Disposition": f"attachment; filename=MediLocker_Mapping_{job_id}.jsonl"},
    )


@app.get("/api/jobs/{job_id}/privacy-report.pdf")
def download_job_privacy_report_pdf(
    job_id: str, request: Request, user: Dict[str, Any] = Depends(require_user)
):
    from .privacy_report_pdf import generate_privacy_integrity_pdf

    job = get_job_detail(job_id, user)
    if job.get("organisation_id"):
        require_org_access(user, job["organisation_id"])

    with get_db() as conn:
        dataset = (
            dict(r)
            if job.get("dataset_id")
            and (r := conn.execute("SELECT * FROM datasets WHERE id = ?", (job["dataset_id"],)).fetchone())
            else None
        )
        organisation = (
            dict(r)
            if job.get("organisation_id")
            and (r := conn.execute("SELECT * FROM organisations WHERE id = ?", (job["organisation_id"],)).fetchone())
            else None
        )
        privacy = (
            dict(r)
            if (r := conn.execute("SELECT * FROM privacy_assessments WHERE job_id = ? ORDER BY created_at DESC LIMIT 1", (job_id,)).fetchone())
            else None
        )
        clinical = (
            dict(r)
            if (r := conn.execute("SELECT * FROM clinical_reports WHERE job_id = ? ORDER BY created_at DESC LIMIT 1", (job_id,)).fetchone())
            else None
        )
        identity = (
            dict(r)
            if (r := conn.execute("SELECT * FROM identity_clusters WHERE job_id = ? ORDER BY created_at DESC LIMIT 1", (job_id,)).fetchone())
            else None
        )
        attack_run = (
            dict(r)
            if (r := conn.execute("SELECT * FROM attack_runs WHERE job_id = ? ORDER BY created_at DESC LIMIT 1", (job_id,)).fetchone())
            else None
        )
        passport = (
            dict(r)
            if (r := conn.execute("SELECT * FROM passports WHERE job_id = ? ORDER BY created_at DESC LIMIT 1", (job_id,)).fetchone())
            else None
        )

    job_out = JOBS_DIR / job_id / "output"
    engine_report = None
    report_json_path = job_out / "report.json"
    if report_json_path.is_file():
        try:
            engine_report = json.loads(report_json_path.read_text(encoding="utf-8"))
        except Exception:
            engine_report = None

    passport_verification = None
    disk_passport = job_out / "privacy_passport.json"
    if passport and disk_passport.is_file():
        try:
            import sys as _sys
            if str(STARTER_DIR) not in _sys.path:
                _sys.path.insert(0, str(STARTER_DIR))
            from verify_passport import verify_passport_bundle  # type: ignore

            manifest_path = job_out / "dataset_manifest.json"
            vres = verify_passport_bundle(
                passport_path=disk_passport,
                output_dir=job_out,
                manifest_path=manifest_path if manifest_path.is_file() else None,
            )
            payload_obj = json.loads(passport.get("passport_json") or "{}")
            disk_root = (
                (payload_obj.get("dataset_provenance") or {}).get("output_dataset_root_hash")
                or passport.get("manifest_hash")
            )
            integrity_ok = bool(vres.get("valid")) and (disk_root == passport.get("manifest_hash"))
            passport_verification = {
                "integrity_valid": integrity_ok,
                "verified_at": passport.get("verified_at") or time.time(),
            }
        except Exception:
            passport_verification = {"integrity_valid": False, "verified_at": None}

    pdf_bytes = generate_privacy_integrity_pdf(
        job=job,
        dataset=dataset,
        organisation=organisation,
        privacy=privacy,
        clinical=clinical,
        identity=identity,
        attack_run=attack_run,
        passport=passport,
        passport_verification=passport_verification,
        engine_report=engine_report,
    )

    record_audit_event(
        action="PRIVACY_REPORT_DOWNLOADED",
        resource_type="job",
        resource_id=job_id,
        outcome="SUCCESS",
        actor_id=user["id"],
        actor_email=user["email"],
        actor_role=user.get("active_role"),
        organisation_id=job.get("organisation_id"),
        details=f"Generated Privacy & Integrity PDF report for job {job_id}",
        ip_address=_client_ip(request),
    )

    return StreamingResponse(
        io.BytesIO(pdf_bytes),
        media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename=MediLocker_Privacy_Integrity_Report_{job_id}.pdf"},
    )


# ==============================================================================
# 5. Privacy, Identity, Clinical, Attack Simulator & Passports
# ==============================================================================


@app.get("/api/privacy/assessments")
def list_privacy_assessments(user: Dict[str, Any] = Depends(require_user)) -> List[Dict[str, Any]]:
    org_ids = _authorised_org_ids(user)
    where_org, params = _org_filter_clause(org_ids, "organisation_id")
    with get_db() as conn:
        rows = conn.execute(
            f"SELECT * FROM privacy_assessments WHERE {where_org} ORDER BY created_at DESC", params
        ).fetchall()
    return [dict(r) for r in rows]


@app.get("/api/privacy/assessments/{assessment_id}")
def get_privacy_assessment(assessment_id: str, user: Dict[str, Any] = Depends(require_user)) -> Dict[str, Any]:
    with get_db() as conn:
        row = conn.execute("SELECT * FROM privacy_assessments WHERE id = ?", (assessment_id,)).fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Assessment not found")
        if row["organisation_id"]:
            require_org_access(user, row["organisation_id"])
    return dict(row)


@app.get("/api/privacy/assessments/{assessment_id}/download")
def download_privacy_assessment_pdf(
    assessment_id: str,
    format: str = Query("pdf", pattern="^pdf$"),
    user: Dict[str, Any] = Depends(require_user),
):
    _ = get_privacy_assessment(assessment_id, user)
    try:
        pdf_bytes, fname = generate_privacy_intelligence_pdf(assessment_id)
    except PdfGenerationError:
        raise HTTPException(status_code=404, detail="Assessment not found")
    except PdfSecurityError as exc:
        raise HTTPException(status_code=422, detail=f"PDF blocked by security gate: {exc}")
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename={fname}"},
    )


def _build_clinical_drift_summary(clinical_row: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    if not clinical_row:
        return {"status": "NOT_MEASURED", "categories": [], "critical_failures": []}
    try:
        details = json.loads(clinical_row.get("details_json") or "{}")
    except Exception:
        details = {}
    raw_cats = details.get("categories") or {}
    if not raw_cats:
        return {"status": "NOT_MEASURED", "categories": [], "critical_failures": []}

    cat_specs = [
        ("dosages", "Medication Dosages"),
        ("medication_names", "Medication Names"),
        ("blood_pressure", "Blood Pressure"),
        ("heart_rate", "Heart Rate"),
        ("temperature", "Temperature"),
        ("spo2", "SpO2 / Oxygen"),
        ("laboratory_measurements", "Lab / Glucose & Biomarkers"),
    ]
    categories: List[Dict[str, Any]] = []
    for key, label in cat_specs:
        c = raw_cats.get(key)
        if not isinstance(c, dict):
            categories.append(
                {
                    "key": key,
                    "label": label,
                    "input_count": 0,
                    "output_count": 0,
                    "preserved_count": 0,
                    "modified_count": 0,
                    "missing_count": 0,
                    "drift_detected": False,
                    "status": "NOT_MEASURED",
                }
            )
            continue
        expected = int(c.get("expected", 0))
        preserved = int(c.get("preserved", 0))
        modified = int(c.get("modified", 0))
        missing = int(c.get("missing", 0))
        unexpected = int(c.get("unexpected", 0))
        output_count = preserved + unexpected
        if expected == 0 and output_count == 0:
            st = "NOT_MEASURED"
            drift_detected = False
        elif modified > 0 or missing > 0:
            st = "DRIFT_DETECTED"
            drift_detected = True
        else:
            st = "PRESERVED"
            drift_detected = False
        categories.append(
            {
                "key": key,
                "label": label,
                "input_count": expected,
                "output_count": output_count,
                "preserved_count": preserved,
                "modified_count": modified,
                "missing_count": missing,
                "drift_detected": drift_detected,
                "status": st,
            }
        )
    return {
        "status": "MEASURED",
        "categories": categories,
        "critical_failures": details.get("critical_failures") or [],
    }


def _build_attack_overview(attack_row: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    if not attack_row:
        return {
            "status": "NOT_EXECUTED",
            "run_id": None,
            "profile": None,
            "risk_score": None,
            "total": 0,
            "blocked": 0,
            "exposed": 0,
            "not_executed": 0,
            "failed": 0,
            "inconclusive": 0,
            "strategies": [],
        }
    try:
        parsed = json.loads(attack_row.get("results_json") or "{}")
    except Exception:
        parsed = {}
    raw_strategies = parsed.get("strategies") or []
    strategies: List[Dict[str, Any]] = []
    counts = {"BLOCKED": 0, "EXPOSED": 0, "NOT_EXECUTED": 0, "FAILED": 0, "INCONCLUSIVE": 0}
    for s in raw_strategies:
        raw_status = str(s.get("status") or "").upper()
        if raw_status in ("BLOCKED", "PASS", "DEFENDED"):
            norm = "BLOCKED"
        elif raw_status in ("EXPOSED", "REIDENTIFIED", "VULNERABLE", "BREACHED"):
            norm = "EXPOSED"
        elif raw_status in ("NOT_EXECUTED", "NOT_RUN", "SKIPPED"):
            norm = "NOT_EXECUTED"
        elif raw_status in ("FAILED", "ERROR"):
            norm = "FAILED"
        else:
            norm = "INCONCLUSIVE"
        counts[norm] += 1
        strategies.append(
            {
                "strategy": s.get("strategy") or s.get("name") or "Unknown Vector",
                "status": norm,
                "matched_records": int(s.get("matched_records", 0)),
                "risk_score": float(s.get("risk_score", 0.0)),
                "details": s.get("details") or "",
            }
        )
    return {
        "status": "MEASURED" if strategies else "NOT_EXECUTED",
        "run_id": attack_row.get("id"),
        "profile": attack_row.get("profile"),
        "risk_score": attack_row.get("risk_score"),
        "total": len(strategies),
        "blocked": counts["BLOCKED"],
        "exposed": counts["EXPOSED"],
        "not_executed": counts["NOT_EXECUTED"],
        "failed": counts["FAILED"],
        "inconclusive": counts["INCONCLUSIVE"],
        "strategies": strategies,
    }


@app.get("/api/privacy-intelligence")
def get_privacy_intelligence(
    job_id: Optional[str] = Query(default=None),
    user: Dict[str, Any] = Depends(require_user),
) -> Dict[str, Any]:
    org_ids = _authorised_org_ids(user)
    where_org, params = _org_filter_clause(org_ids, "j.organisation_id")
    with get_db() as conn:
        job_rows = [
            dict(r)
            for r in conn.execute(
                f"""
                SELECT j.id, j.dataset_id, j.organisation_id, j.status, j.release_decision,
                       j.files_total, j.files_sanitized, j.files_quarantined,
                       j.records_processed, j.identifiers_detected, j.created_at, j.completed_at,
                       d.name as dataset_name, o.name as organisation_name
                FROM jobs j
                LEFT JOIN datasets d ON j.dataset_id = d.id
                LEFT JOIN organisations o ON j.organisation_id = o.id
                WHERE {where_org}
                ORDER BY j.created_at DESC
                LIMIT 25
                """,
                params,
            ).fetchall()
        ]

    assessments = list_privacy_assessments(user)
    selected_job: Optional[Dict[str, Any]] = None
    if job_id:
        for j in job_rows:
            if j["id"] == job_id:
                selected_job = j
                break
        if not selected_job:
            raise HTTPException(status_code=404, detail="Job not found or access denied")
    elif assessments:
        target_jid = assessments[0]["job_id"]
        selected_job = next((j for j in job_rows if j["id"] == target_jid), None) or (job_rows[0] if job_rows else None)
    elif job_rows:
        selected_job = job_rows[0]

    selected_job_id = selected_job["id"] if selected_job else None
    selected_assessment = (
        next((a for a in assessments if a["job_id"] == selected_job_id), None)
        if selected_job_id
        else (assessments[0] if assessments else None)
    )

    clinical_row: Optional[Dict[str, Any]] = None
    attack_row: Optional[Dict[str, Any]] = None
    if selected_job_id:
        with get_db() as conn:
            c_row = conn.execute("SELECT * FROM clinical_reports WHERE job_id = ?", (selected_job_id,)).fetchone()
            if c_row:
                clinical_row = dict(c_row)
            a_row = conn.execute(
                "SELECT * FROM attack_runs WHERE job_id = ? ORDER BY created_at DESC LIMIT 1",
                (selected_job_id,),
            ).fetchone()
            if a_row:
                attack_row = dict(a_row)

    clinical_drift = _build_clinical_drift_summary(clinical_row)
    attack_overview = _build_attack_overview(attack_row)

    if clinical_row:
        try:
            c_det = json.loads(clinical_row.get("details_json") or "{}")
        except Exception:
            c_det = {}
        clinical_fidelity: Dict[str, Any] = {
            "status": "MEASURED",
            "expected_values": int(clinical_row.get("expected_values", 0)),
            "preserved_values": int(clinical_row.get("preserved_values", 0)),
            "modified_values": int(clinical_row.get("modified_values", 0)),
            "missing_values": int(clinical_row.get("missing_values", 0)),
            "exact_fidelity_pct": c_det.get("exact_fidelity_pct"),
            "lab_integrity": clinical_row.get("lab_integrity"),
            "medication_integrity": clinical_row.get("medication_integrity"),
            "dosage_integrity": clinical_row.get("dosage_integrity"),
            "vital_integrity": clinical_row.get("vital_integrity"),
            "fhir_integrity": clinical_row.get("fhir_integrity") or "NOT_MEASURED",
            "fhir_bundles_checked": int(c_det.get("fhir_bundles_checked", 0)),
            "fhir_bundles_valid": int(c_det.get("fhir_bundles_valid", 0)),
        }
    else:
        clinical_fidelity = {"status": "NOT_MEASURED"}

    if not assessments and not selected_job:
        return {
            "status": "NOT_MEASURED",
            "assessments_count": 0,
            "total_pii_detected": 0,
            "total_residual_leakage": 0,
            "canary_status": "NOT_RUN",
            "reid_risk_level": "NOT_MEASURED",
            "risk_map": None,
            "assessments": [],
            "jobs": [],
            "selected_job_id": None,
            "selected_job": None,
            "clinical_fidelity": clinical_fidelity,
            "clinical_drift": clinical_drift,
            "attack_overview": attack_overview,
            "before_after": {"status": "NOT_MEASURED"},
            "release_readiness": {"status": "NOT_MEASURED", "reasons": ["No dataset processing jobs recorded yet."]},
            "last_updated": None,
        }

    risk_map = None
    if selected_assessment:
        try:
            det = json.loads(selected_assessment.get("details_json") or "{}")
            risk_map = det.get("risk_map")
        except Exception:
            risk_map = None

    pii_det = int(selected_assessment["pii_detected"]) if selected_assessment else int((selected_job or {}).get("identifiers_detected") or 0)
    res_leak = int(selected_assessment["residual_leakage"]) if selected_assessment else 0
    canary_st = selected_assessment["canary_status"] if selected_assessment else "NOT_RUN"
    reid_lvl = selected_assessment["reid_risk_level"] if selected_assessment else "NOT_MEASURED"

    before_after = {
        "status": "MEASURED" if selected_assessment else "NOT_MEASURED",
        "before_pii_detected": pii_det,
        "after_residual_leakage": res_leak,
        "canary_planted": int(selected_assessment["canary_planted"]) if selected_assessment else 0,
        "canary_leaks": int(selected_assessment["canary_leaks"]) if selected_assessment else 0,
        "pre_risk_categories": (risk_map or {}).get("pre_categories") or {},
        "post_risk_categories": (risk_map or {}).get("post_categories") or {},
        "reid_risk_level": reid_lvl,
    }

    rel_dec = str((selected_job or {}).get("release_decision") or "PENDING").upper()
    readiness_reasons: List[str] = []
    if rel_dec == "BLOCKED" or canary_st == "FAILED" or res_leak > 0 or attack_overview["exposed"] > 0:
        readiness_status = "BLOCKED"
        if canary_st == "FAILED":
            readiness_reasons.append("Canary leakage detected; release strictly blocked.")
        if res_leak > 0:
            readiness_reasons.append(f"Residual PII leakage ({res_leak}) detected in sanitized output.")
        if attack_overview["exposed"] > 0:
            readiness_reasons.append(f"{attack_overview['exposed']} attack vector(s) exposed records.")
        if not readiness_reasons:
            readiness_reasons.append("Release gate blocked output due to privacy or integrity policy violation.")
    elif rel_dec in ("APPROVED_WITH_WARNINGS", "QUARANTINED") or ((selected_job or {}).get("files_quarantined") or 0) > 0:
        readiness_status = "PASS_WITH_WARNINGS"
        if ((selected_job or {}).get("files_quarantined") or 0) > 0:
            readiness_reasons.append(
                f"{selected_job['files_quarantined']} file(s) quarantined; remaining output passed privacy & clinical checks."
            )
        else:
            readiness_reasons.append("Approved with non-blocking advisory warnings.")
    elif rel_dec == "APPROVED":
        readiness_status = "PASS"
        readiness_reasons.append("All privacy, canary, clinical integrity, and release gate checks passed.")
    else:
        readiness_status = "NOT_MEASURED"
        readiness_reasons.append(f"Job release decision is currently {rel_dec}.")

    last_updated = (
        (selected_job or {}).get("completed_at")
        or (selected_assessment or {}).get("created_at")
        or (selected_job or {}).get("created_at")
    )

    return {
        "status": "MEASURED" if selected_assessment else "NOT_MEASURED",
        "assessments_count": len(assessments),
        "total_pii_detected": sum(int(a["pii_detected"]) for a in assessments),
        "total_residual_leakage": sum(int(a["residual_leakage"]) for a in assessments),
        "canary_status": canary_st,
        "reid_risk_level": reid_lvl,
        "risk_map": risk_map,
        "assessments": assessments,
        "jobs": job_rows,
        "selected_job_id": selected_job_id,
        "selected_job": selected_job,
        "clinical_fidelity": clinical_fidelity,
        "clinical_drift": clinical_drift,
        "attack_overview": attack_overview,
        "before_after": before_after,
        "release_readiness": {
            "status": readiness_status,
            "decision": rel_dec,
            "reasons": readiness_reasons,
        },
        "last_updated": last_updated,
    }


@app.get("/api/quarantine")
def list_quarantined_files(
    job_id: Optional[str] = Query(default=None),
    user: Dict[str, Any] = Depends(require_user),
) -> Dict[str, Any]:
    """Return safe, PII-free metadata for quarantined files across authorised organisations."""
    org_ids = _authorised_org_ids(user)
    where_org, params = _org_filter_clause(org_ids, "j.organisation_id")
    query = f"""
        SELECT j.id as job_id, j.dataset_id, j.organisation_id, j.files_quarantined,
               j.created_at, j.completed_at, j.summary_json,
               d.name as dataset_name, o.name as organisation_name
        FROM jobs j
        LEFT JOIN datasets d ON j.dataset_id = d.id
        LEFT JOIN organisations o ON j.organisation_id = o.id
        WHERE {where_org}
    """
    if job_id:
        query += " AND j.id = ?"
        params = list(params) + [job_id]
    query += " ORDER BY j.created_at DESC LIMIT 50"

    with get_db() as conn:
        rows = [dict(r) for r in conn.execute(query, params).fetchall()]

    items: List[Dict[str, Any]] = []
    jobs_with_quarantine = 0
    for row in rows:
        q_count = int(row.get("files_quarantined") or 0)
        try:
            summary = json.loads(row.get("summary_json") or "{}")
        except Exception:
            summary = {}
        q_files = summary.get("quarantined_files") or []
        if q_count > 0 or q_files:
            jobs_with_quarantine += 1
        if q_files:
            for item in q_files:
                items.append(
                    {
                        **item,
                        "dataset_name": row.get("dataset_name") or "Synthetic Dataset",
                        "organisation_name": row.get("organisation_name") or "Default Org",
                        "download_allowed": False,
                    }
                )
        elif q_count > 0:
            items.append(
                {
                    "quarantine_id": f"qrn-{row['job_id'][-6:]}-001",
                    "opaque_ref": f"QRN-{row['job_id'][-8:].upper()}",
                    "job_id": row["job_id"],
                    "dataset_id": row.get("dataset_id"),
                    "dataset_name": row.get("dataset_name") or "Synthetic Dataset",
                    "organisation_name": row.get("organisation_name") or "Default Org",
                    "file_type": "unknown",
                    "size_bytes": None,
                    "quarantined_at": row.get("completed_at") or row.get("created_at"),
                    "stage_failed": "SANITIZATION_PIPELINE",
                    "error_code": "ERR_POLICY_QUARANTINE",
                    "reason": f"{q_count} file(s) isolated by MediLocker quarantine policy.",
                    "recommended_action": "Review dataset formatting and compliance rules with a Privacy Officer.",
                    "retry_safe": False,
                    "resolution_status": "QUARANTINED_PENDING_REVIEW",
                    "requires_manual_review": True,
                    "download_allowed": False,
                }
            )

    pending_review_count = sum(1 for i in items if i.get("requires_manual_review"))
    return {
        "status": "OK",
        "total_quarantined": len(items),
        "jobs_with_quarantine": jobs_with_quarantine,
        "pending_review_count": pending_review_count,
        "items": items,
    }


@app.get("/api/identity/clusters")
@app.get("/api/identity-graph")
def list_identity_clusters(
    job_id: Optional[str] = None, user: Dict[str, Any] = Depends(require_user)
) -> Dict[str, Any]:
    org_ids = _authorised_org_ids(user)
    where_org, params = _org_filter_clause(org_ids, "organisation_id")
    with get_db() as conn:
        if job_id:
            row = conn.execute(
                f"SELECT * FROM identity_clusters WHERE job_id = ? AND {where_org}",
                [job_id] + params,
            ).fetchone()
        else:
            row = conn.execute(
                f"SELECT * FROM identity_clusters WHERE {where_org} ORDER BY created_at DESC LIMIT 1",
                params,
            ).fetchone()

    if not row:
        return {
            "status": "NOT_MEASURED",
            "nodes": [],
            "edges": [],
            "total_patients": 0,
            "cross_hospital_links": 0,
            "precision": None,
            "recall": None,
            "f05": None,
            "false_merges": 0,
            "abstentions": 0,
            "conflicts": 0,
        }

    data = dict(row)
    graph = json.loads(data.get("graph_json") or "{}")
    return {
        "status": "MEASURED",
        "id": data["id"],
        "job_id": data["job_id"],
        "nodes": graph.get("nodes", []),
        "edges": graph.get("edges", []),
        "clusters": graph.get("clusters", []),
        "total_patients": data["total_patients"],
        "cross_hospital_links": data["cross_hospital_links"],
        "precision": data["precision"],
        "recall": data["recall"],
        "f05": data["f05"],
        "false_merges": data["false_merges"],
        "abstentions": data["abstentions"],
        "conflicts": data["conflicts"],
    }


@app.get("/api/clinical/reports")
def list_clinical_reports(user: Dict[str, Any] = Depends(require_user)) -> List[Dict[str, Any]]:
    org_ids = _authorised_org_ids(user)
    where_org, params = _org_filter_clause(org_ids, "organisation_id")
    with get_db() as conn:
        rows = conn.execute(
            f"SELECT * FROM clinical_reports WHERE {where_org} ORDER BY created_at DESC", params
        ).fetchall()
    return [dict(r) for r in rows]


@app.get("/api/clinical/reports/{report_id}")
def get_clinical_report(report_id: str, user: Dict[str, Any] = Depends(require_user)) -> Dict[str, Any]:
    with get_db() as conn:
        row = conn.execute("SELECT * FROM clinical_reports WHERE id = ?", (report_id,)).fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Clinical report not found")
        if row["organisation_id"]:
            require_org_access(user, row["organisation_id"])
    return dict(row)


@app.get("/api/clinical/reports/{report_id}/download")
def download_clinical_report_pdf(
    report_id: str,
    format: str = Query("pdf", pattern="^pdf$"),
    user: Dict[str, Any] = Depends(require_user),
):
    _ = get_clinical_report(report_id, user)
    try:
        pdf_bytes, fname = generate_clinical_integrity_pdf(report_id)
    except PdfGenerationError:
        raise HTTPException(status_code=404, detail="Clinical report not found")
    except PdfSecurityError as exc:
        raise HTTPException(status_code=422, detail=f"PDF blocked by security gate: {exc}")
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename={fname}"},
    )


@app.get("/api/threat-lab")
def get_threat_lab(user: Dict[str, Any] = Depends(require_user)) -> Dict[str, Any]:
    org_ids = _authorised_org_ids(user)
    where_org, params = _org_filter_clause(org_ids, "organisation_id")
    with get_db() as conn:
        runs = [
            dict(r)
            for r in conn.execute(
                f"SELECT * FROM attack_runs WHERE {where_org} ORDER BY created_at DESC LIMIT 20", params
            ).fetchall()
        ]
    if not runs:
        return {
            "status": "NOT_RUN",
            "risk_score": None,
            "attack_simulations": [],
            "history": [],
        }
    latest = runs[0]
    parsed = json.loads(latest.get("results_json") or "{}")
    return {
        "status": "MEASURED",
        "risk_score": latest["risk_score"],
        "attack_simulations": parsed.get("strategies", []),
        "history": runs,
    }


class AttackRunBody(BaseModel):
    job_id: str
    profile: str = "standard-7-vector"


@app.post("/api/attack-simulator/run")
def run_attack_simulator(
    body: AttackRunBody, request: Request, user: Dict[str, Any] = Depends(require_user)
) -> Dict[str, Any]:
    job = get_job_detail(body.job_id, user)
    if job.get("organisation_id"):
        require_org_access(user, job["organisation_id"], [ROLE_PLATFORM_ADMIN, ROLE_ORG_ADMIN, ROLE_PRIVACY_OFFICER])
    res = run_attack_simulation_for_job(
        job_id=job["id"],
        dataset_id=job.get("dataset_id"),
        organisation_id=job.get("organisation_id"),
        profile=body.profile,
        actor_id=user["id"],
    )
    record_audit_event(
        action="ATTACK_SIMULATION_RUN",
        resource_type="attack_run",
        resource_id=res["id"],
        outcome="SUCCESS",
        actor_id=user["id"],
        actor_email=user["email"],
        actor_role=user.get("active_role"),
        organisation_id=job.get("organisation_id"),
        details=f"Executed profile {body.profile} on job {job['id']}",
        ip_address=_client_ip(request),
    )
    return res


@app.get("/api/attack-simulator/runs/{run_id}/download")
def download_attack_simulation_pdf(
    run_id: str,
    format: str = Query("pdf", pattern="^pdf$"),
    user: Dict[str, Any] = Depends(require_user),
):
    with get_db() as conn:
        row = conn.execute("SELECT * FROM attack_runs WHERE id = ?", (run_id,)).fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Attack simulation run not found")
        if row["organisation_id"]:
            require_org_access(user, row["organisation_id"])
    try:
        pdf_bytes, fname = generate_attack_simulation_pdf(run_id)
    except PdfGenerationError:
        raise HTTPException(status_code=404, detail="Attack simulation run not found")
    except PdfSecurityError as exc:
        raise HTTPException(status_code=422, detail=f"PDF blocked by security gate: {exc}")
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename={fname}"},
    )


@app.get("/api/passports")
def list_passports(user: Dict[str, Any] = Depends(require_user)) -> List[Dict[str, Any]]:
    org_ids = _authorised_org_ids(user)
    where_org, params = _org_filter_clause(org_ids, "p.organisation_id")
    with get_db() as conn:
        rows = conn.execute(
            f"""
            SELECT p.*, d.name as dataset_name, o.name as organisation_name
            FROM passports p
            LEFT JOIN datasets d ON d.id = p.dataset_id
            LEFT JOIN organisations o ON o.id = p.organisation_id
            WHERE {where_org}
            ORDER BY p.created_at DESC
            """,
            params,
        ).fetchall()
    return [dict(r) for r in rows]


@app.get("/api/passports/{passport_id}")
def get_passport(passport_id: str, user: Dict[str, Any] = Depends(require_user)) -> Dict[str, Any]:
    with get_db() as conn:
        row = conn.execute("SELECT * FROM passports WHERE id = ?", (passport_id,)).fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Privacy Passport not found")
        if row["organisation_id"]:
            require_org_access(user, row["organisation_id"])
    data = dict(row)
    data["payload"] = json.loads(data["passport_json"])
    return data


@app.post("/api/passports/{passport_id}/verify")
def verify_passport(
    passport_id: str, request: Request, user: Dict[str, Any] = Depends(require_user)
) -> Dict[str, Any]:
    data = get_passport(passport_id, user)
    job_id = data.get("job_id")
    job_out = (JOBS_DIR / job_id / "output") if job_id else None
    disk_passport = (job_out / "privacy_passport.json") if job_out else None

    verification_details: List[str] = []
    if disk_passport and disk_passport.is_file():
        import sys as _sys
        if str(STARTER_DIR) not in _sys.path:
            _sys.path.insert(0, str(STARTER_DIR))
        from verify_passport import verify_passport_bundle  # type: ignore

        manifest_path = job_out / "dataset_manifest.json"
        vres = verify_passport_bundle(
            passport_path=disk_passport,
            output_dir=job_out,
            manifest_path=manifest_path if manifest_path.is_file() else None,
        )
        disk_root = (
            (data["payload"].get("dataset_provenance") or {}).get("output_dataset_root_hash")
            or data["manifest_hash"]
        )
        integrity_ok = bool(vres.get("valid")) and (disk_root == data["manifest_hash"])
        verification_details = list(vres.get("details") or [])
        if disk_root != data["manifest_hash"]:
            integrity_ok = False
            verification_details.append("Stored DB manifest_hash does not match passport payload.")
    else:
        recomputed = hashlib.sha256(
            json.dumps(data["payload"], sort_keys=True).encode("utf-8")
        ).hexdigest()
        integrity_ok = recomputed == data["manifest_hash"]
        verification_details = ["Canonical payload SHA-256 verified." if integrity_ok else "Canonical payload SHA-256 mismatch."]

    now = time.time()
    if integrity_ok:
        with get_db() as conn:
            conn.execute("UPDATE passports SET verified_at = ? WHERE id = ?", (now, passport_id))
    record_audit_event(
        action="PASSPORT_VERIFIED",
        resource_type="passport",
        resource_id=passport_id,
        outcome="SUCCESS" if integrity_ok else "FAILED",
        actor_id=user["id"],
        actor_email=user["email"],
        actor_role=user.get("active_role"),
        organisation_id=data.get("organisation_id"),
        ip_address=_client_ip(request),
    )
    return {
        "passport_id": passport_id,
        "integrity_valid": integrity_ok,
        "signature_status": data["signature_status"],
        "manifest_hash": data["manifest_hash"],
        "details": verification_details,
        "verified_at": now if integrity_ok else None,
    }


@app.get("/api/passports/{passport_id}/download")
def download_passport(
    passport_id: str,
    format: str = Query("json", pattern="^(json|html|pdf)$"),
    user: Dict[str, Any] = Depends(require_user),
):
    data = get_passport(passport_id, user)
    if format == "pdf":
        try:
            pdf_bytes, fname = generate_privacy_passport_pdf(passport_id)
        except PdfGenerationError:
            raise HTTPException(status_code=404, detail="Privacy Passport not found")
        except PdfSecurityError as exc:
            raise HTTPException(status_code=422, detail=f"PDF blocked by security gate: {exc}")
        return Response(
            content=pdf_bytes,
            media_type="application/pdf",
            headers={"Content-Disposition": f"attachment; filename={fname}"},
        )
    if format == "json":
        return Response(
            content=json.dumps(
                {
                    "passport_id": data["id"],
                    "signature_status": data["signature_status"],
                    "manifest_hash": data["manifest_hash"],
                    "payload": data["payload"],
                },
                indent=2,
            ),
            media_type="application/json",
            headers={"Content-Disposition": f"attachment; filename=PrivacyPassport_{passport_id}.json"},
        )
    metrics = data["payload"].get("metrics", {})
    report_html = f"""<!doctype html>
<html><head><meta charset="utf-8"><title>MediLocker Privacy Passport {html.escape(passport_id)}</title>
<style>body{{font-family:system-ui,sans-serif;max-width:720px;margin:40px auto;color:#050505}}
.box{{border:1px solid #dcdcdc;border-radius:8px;padding:20px;margin-top:16px}}</style></head>
<body>
<h1>MediLocker Privacy Passport</h1>
<p><strong>Passport ID:</strong> {html.escape(passport_id)}</p>
<p><strong>Signature Status:</strong> {html.escape(data['signature_status'])} (Hash-Verified Manifest)</p>
<p><strong>Manifest SHA-256:</strong> <code>{html.escape(data['manifest_hash'])}</code></p>
<p><strong>Release Decision:</strong> {html.escape(str(data['payload'].get('release_decision', '')))}</p>
<div class="box"><h3>Measured Metrics</h3>
<pre>{html.escape(json.dumps(metrics, indent=2))}</pre></div>
</body></html>"""
    return HTMLResponse(
        content=report_html,
        headers={"Content-Disposition": f"attachment; filename=PrivacyPassport_{passport_id}.html"},
    )


# ==============================================================================
# 6. Research Collaboration, Audit Trail & Settings
# ==============================================================================


@app.get("/api/research/requests")
def list_research_requests(user: Dict[str, Any] = Depends(require_user)) -> List[Dict[str, Any]]:
    with get_db() as conn:
        rows = [
            dict(r)
            for r in conn.execute("SELECT * FROM research_requests ORDER BY created_at DESC").fetchall()
        ]
    return rows


class NewResearchBody(BaseModel):
    title: str
    institution: str
    purpose: str = ""
    dataset_id: Optional[str] = None


@app.post("/api/research/requests")
def create_research_request(
    body: NewResearchBody,
    request: Request,
    user: Dict[str, Any] = Depends(
        require_roles([ROLE_PLATFORM_ADMIN, ROLE_ORG_ADMIN, ROLE_PRIVACY_OFFICER, ROLE_RESEARCHER])
    ),
) -> Dict[str, Any]:
    req_id = f"req-{int(time.time())}-{secrets.token_hex(3)}"
    now = time.time()
    with get_db() as conn:
        conn.execute(
            """
            INSERT INTO research_requests (
                id, title, requestor_org, target_orgs, purpose, status, created_at,
                datasets_requested, release_simulated, organisation_id, dataset_id, created_by
            ) VALUES (?, ?, ?, ?, ?, 'SUBMITTED', ?, ?, 0, ?, ?, ?)
            """,
            (
                req_id,
                body.title.strip(),
                body.institution.strip(),
                json.dumps([user.get("active_org_id") or ""]),
                body.purpose.strip(),
                now,
                json.dumps([body.dataset_id] if body.dataset_id else []),
                user.get("active_org_id"),
                body.dataset_id,
                user["id"],
            ),
        )
        row = dict(conn.execute("SELECT * FROM research_requests WHERE id = ?", (req_id,)).fetchone())
    record_audit_event(
        action="RESEARCH_REQUEST_SUBMITTED",
        resource_type="research_request",
        resource_id=req_id,
        outcome="SUCCESS",
        actor_id=user["id"],
        actor_email=user["email"],
        actor_role=user.get("active_role"),
        organisation_id=user.get("active_org_id"),
        ip_address=_client_ip(request),
    )
    return row


@app.post("/api/research/requests/{req_id}/approve")
def approve_research_request(
    req_id: str,
    request: Request,
    user: Dict[str, Any] = Depends(require_roles([ROLE_PLATFORM_ADMIN, ROLE_ORG_ADMIN, ROLE_PRIVACY_OFFICER])),
) -> Dict[str, str]:
    with get_db() as conn:
        row = conn.execute("SELECT * FROM research_requests WHERE id = ?", (req_id,)).fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Research request not found")
        conn.execute(
            "UPDATE research_requests SET status = 'APPROVED', reviewed_by = ?, reviewed_at = ? WHERE id = ?",
            (user["id"], time.time(), req_id),
        )
    record_audit_event(
        action="RESEARCH_REQUEST_APPROVED",
        resource_type="research_request",
        resource_id=req_id,
        outcome="APPROVED",
        actor_id=user["id"],
        actor_email=user["email"],
        actor_role=user.get("active_role"),
        organisation_id=row["organisation_id"],
        ip_address=_client_ip(request),
    )
    return {"status": "APPROVED"}


@app.post("/api/research/requests/{req_id}/reject")
def reject_research_request(
    req_id: str,
    request: Request,
    user: Dict[str, Any] = Depends(require_roles([ROLE_PLATFORM_ADMIN, ROLE_ORG_ADMIN, ROLE_PRIVACY_OFFICER])),
) -> Dict[str, str]:
    with get_db() as conn:
        row = conn.execute("SELECT * FROM research_requests WHERE id = ?", (req_id,)).fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Research request not found")
        conn.execute(
            "UPDATE research_requests SET status = 'REJECTED', reviewed_by = ?, reviewed_at = ? WHERE id = ?",
            (user["id"], time.time(), req_id),
        )
    record_audit_event(
        action="RESEARCH_REQUEST_REJECTED",
        resource_type="research_request",
        resource_id=req_id,
        outcome="REJECTED",
        actor_id=user["id"],
        actor_email=user["email"],
        actor_role=user.get("active_role"),
        organisation_id=row["organisation_id"],
        ip_address=_client_ip(request),
    )
    return {"status": "REJECTED"}


@app.get("/api/audit/events")
@app.get("/api/audit")
def list_audit_events(
    page: int = Query(1, ge=1),
    page_size: int = Query(25, ge=1, le=100),
    action: Optional[str] = None,
    user: Dict[str, Any] = Depends(require_user),
) -> Dict[str, Any]:
    org_ids = _authorised_org_ids(user)
    where_org, params = _org_filter_clause(org_ids, "organisation_id")
    clauses = [f"({where_org} OR organisation_id IS NULL)"]
    if action:
        clauses.append("action = ?")
        params.append(action)
    where_sql = " AND ".join(clauses)
    offset = (page - 1) * page_size

    with get_db() as conn:
        total = conn.execute(
            f"SELECT COUNT(*) as c FROM audit_events WHERE {where_sql}", params
        ).fetchone()["c"]
        rows = [
            dict(r)
            for r in conn.execute(
                f"SELECT * FROM audit_events WHERE {where_sql} ORDER BY timestamp DESC LIMIT ? OFFSET ?",
                params + [page_size, offset],
            ).fetchall()
        ]
    return {"events": rows, "total": total, "page": page, "page_size": page_size}


@app.get("/api/audit/export")
def export_audit_trail_pdf(
    organisation_id: Optional[str] = None,
    start_ts: Optional[float] = None,
    end_ts: Optional[float] = None,
    user: Dict[str, Any] = Depends(require_user),
):
    target_org = organisation_id or user.get("active_org_id")
    if target_org:
        require_org_access(user, target_org)
    elif user.get("platform_role") != ROLE_PLATFORM_ADMIN:
        raise HTTPException(status_code=403, detail="Organisation access required")

    org_name = "All Authorised Organisations"
    if target_org:
        with get_db() as conn:
            orow = conn.execute("SELECT name FROM organisations WHERE id = ?", (target_org,)).fetchone()
            org_name = orow["name"] if orow else target_org
    try:
        pdf_bytes, fname = generate_audit_trail_pdf(
            organisation_id=target_org,
            organisation_name=org_name,
            start_ts=start_ts,
            end_ts=end_ts,
        )
    except PdfSecurityError as exc:
        raise HTTPException(status_code=422, detail=f"PDF blocked by security gate: {exc}")
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename={fname}"},
    )


@app.get("/api/settings")
def get_settings(user: Dict[str, Any] = Depends(require_user)) -> Dict[str, Any]:
    smtp = get_smtp_config()
    google = get_google_config()
    with get_db() as conn:
        saved = {
            r["key"]: r["value"]
            for r in conn.execute("SELECT key, value FROM settings").fetchall()
        }
    return {
        "user": {k: v for k, v in user.items() if k != "raw_token"},
        "smtp_configured": smtp["configured"],
        "google_configured": google["configured"],
        "raksha_secret_set": bool(os.environ.get("RAKSHA_SECRET")),
        "output_format": saved.get("output_format", "sanitized+report+records"),
        "quarantine_threshold": float(saved.get("quarantine_threshold", "0.5")),
        "multilingual_enabled": saved.get("multilingual_enabled", "true") == "true",
    }


class SettingsUpdateBody(BaseModel):
    output_format: Optional[str] = None
    quarantine_threshold: Optional[float] = None
    multilingual_enabled: Optional[bool] = None


@app.post("/api/settings")
def update_settings(
    body: SettingsUpdateBody,
    request: Request,
    user: Dict[str, Any] = Depends(require_roles([ROLE_PLATFORM_ADMIN, ROLE_ORG_ADMIN, ROLE_PRIVACY_OFFICER])),
) -> Dict[str, Any]:
    with get_db() as conn:
        if body.output_format is not None:
            conn.execute(
                "INSERT OR REPLACE INTO settings (key, value) VALUES ('output_format', ?)",
                (body.output_format,),
            )
        if body.quarantine_threshold is not None:
            conn.execute(
                "INSERT OR REPLACE INTO settings (key, value) VALUES ('quarantine_threshold', ?)",
                (str(body.quarantine_threshold),),
            )
        if body.multilingual_enabled is not None:
            conn.execute(
                "INSERT OR REPLACE INTO settings (key, value) VALUES ('multilingual_enabled', ?)",
                ("true" if body.multilingual_enabled else "false",),
            )
    record_audit_event(
        action="SETTINGS_UPDATED",
        resource_type="settings",
        outcome="SUCCESS",
        actor_id=user["id"],
        actor_email=user["email"],
        actor_role=user.get("active_role"),
        organisation_id=user.get("active_org_id"),
        ip_address=_client_ip(request),
    )
    return get_settings(user)
