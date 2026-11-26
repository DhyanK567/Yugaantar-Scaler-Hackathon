"""GuptKavach / MediLocker Healthcare Privacy Firewall Backend API.
Built with FastAPI — Single Source of Truth integration layer.
Zero sanitisation logic is duplicated here; calls the official standalone engine.
"""
from __future__ import annotations

import json
import os
import re
import time
import zipfile
import io
from pathlib import Path
from typing import Any, Dict, List, Optional

from fastapi import FastAPI, File, Form, HTTPException, Query, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from .database import get_db, init_db, record_audit_event, sanitize_log_text
from .engine_adapter import (
    ATTACK_VECTOR_META,
    DEV_INPUT,
    STARTER_DIR,
    compute_bytes_sha256,
    compute_file_sha256,
    evaluate_clinical_integrity_for_job,
    execute_engine,
    load_policy_dict,
    parse_identity_continuity_graph,
    read_job_manifest,
    read_job_passport,
    read_job_report,
    run_attack_simulation_for_job,
    validate_uploaded_file,
    verify_passport_for_job,
)

init_db()

app = FastAPI(
    title="GuptKavach / MediLocker Privacy Firewall API",
    version="1.0.0",
    description="Offline CPU-only Healthcare Privacy Firewall & Governance Console API",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

DATA_DIR = Path(__file__).resolve().parent.parent / "data"
JOBS_DIR = DATA_DIR / "jobs"
DATASETS_DIR = DATA_DIR / "datasets"
JOBS_DIR.mkdir(parents=True, exist_ok=True)
DATASETS_DIR.mkdir(parents=True, exist_ok=True)


def sanitize_filename(name: str) -> str:
    cleaned = re.sub(r"[^a-zA-Z0-9_.-]", "_", Path(name).name)
    if not cleaned or cleaned.startswith("."):
        cleaned = f"file_{int(time.time())}.dat"
    return cleaned


def _resolve_job_row(job_id: Optional[str] = None, org_id: Optional[str] = None, dataset_id: Optional[str] = None) -> Optional[Dict[str, Any]]:
    """Resolve the exact job from SQLite matching job_id or latest for org_id/dataset_id."""
    with get_db() as conn:
        if job_id:
            row = conn.execute("SELECT * FROM jobs WHERE id = ?", (job_id,)).fetchone()
            return dict(row) if row else None

        clauses = []
        params: List[Any] = []
        if org_id:
            clauses.append("org_id = ?")
            params.append(org_id)
        if dataset_id:
            clauses.append("dataset_id = ?")
            params.append(dataset_id)

        where_sql = ("WHERE " + " AND ".join(clauses)) if clauses else ""
        row = conn.execute(
            f"SELECT * FROM jobs {where_sql} ORDER BY created_at DESC LIMIT 1",
            tuple(params),
        ).fetchone()
        return dict(row) if row else None


def _job_output_path(job: Optional[Dict[str, Any]]) -> Optional[Path]:
    if not job or not job.get("output_dir"):
        return None
    p = Path(job["output_dir"])
    return p if p.is_dir() else None


# ==============================================================================
# 1. Health & Dashboard
# ==============================================================================


@app.get("/api/health")
def get_health() -> Dict[str, Any]:
    return {
        "status": "healthy",
        "engine": "GuptKavach Offline Privacy Engine",
        "engine_version": "1.0-deterministic",
        "mode": "offline-cpu-only",
        "compliance": ["Track 3 Secret Wards", "FHIR R4", "DPDP Act (India)", "ABHA/NDHM"],
        "timestamp": time.time(),
    }


@app.get("/api/dashboard")
def get_dashboard(
    org_id: Optional[str] = Query(None),
    job_id: Optional[str] = Query(None),
) -> Dict[str, Any]:
    latest_job = _resolve_job_row(job_id=job_id, org_id=org_id)

    with get_db() as conn:
        if org_id:
            recent_jobs = [
                dict(r) for r in conn.execute(
                    "SELECT * FROM jobs WHERE org_id = ? ORDER BY created_at DESC LIMIT 10",
                    (org_id,),
                ).fetchall()
            ]
            recent_audits = [
                dict(r) for r in conn.execute(
                    "SELECT * FROM audit_logs WHERE org_id = ? ORDER BY timestamp DESC LIMIT 10",
                    (org_id,),
                ).fetchall()
            ]
        else:
            recent_jobs = [
                dict(r) for r in conn.execute(
                    "SELECT * FROM jobs ORDER BY created_at DESC LIMIT 10"
                ).fetchall()
            ]
            recent_audits = [
                dict(r) for r in conn.execute(
                    "SELECT * FROM audit_logs ORDER BY timestamp DESC LIMIT 10"
                ).fetchall()
            ]

    if not latest_job:
        return {
            "has_data": False,
            "org_id": org_id,
            "latest_job": None,
            "summary": {
                "release_readiness": "NOT_EVALUATED",
                "files_processed": 0,
                "files_sanitized": 0,
                "files_quarantined": 0,
                "records_processed": 0,
                "records_linked": 0,
                "identifiers_detected": 0,
                "clinical_preservation": "NOT_MEASURED",
                "identity_precision": "NOT_MEASURED",
                "canary_status": "NOT_MEASURED",
                "critical_risks": "NOT_MEASURED",
                "pending_checks": 0,
            },
            "recent_jobs": recent_jobs,
            "recent_audits": recent_audits,
            "engine_status": {
                "state": "Operational & Armed (No Jobs Yet for Selection)",
                "mode": "Offline CPU-Only",
            },
        }

    out_dir = _job_output_path(latest_job)
    report = read_job_report(out_dir) if out_dir else {}
    pi = report.get("privacy_intelligence", {})
    risk_sum = pi.get("risk_summary", {})
    post_cats = risk_sum.get("post_categories", {})
    ci = report.get("clinical_integrity", {})

    critical_risks = int(post_cats.get("CRITICAL", 0) or 0) + int(post_cats.get("HIGH", 0) or 0)
    fhir_ok = ci.get("fhir_validation_passed", True)
    pending_checks = 0
    if latest_job.get("release_decision") in ("REVIEW_REQUIRED", "NOT_EVALUATED"):
        pending_checks += 1

    return {
        "has_data": True,
        "org_id": org_id,
        "latest_job": latest_job,
        "summary": {
            "release_readiness": latest_job.get("release_decision", "NOT_EVALUATED"),
            "files_processed": latest_job.get("files_total", 0),
            "files_sanitized": latest_job.get("files_sanitized", 0),
            "files_quarantined": latest_job.get("files_quarantined", 0),
            "records_processed": latest_job.get("records_processed", 0),
            "records_linked": latest_job.get("records_linked", 0),
            "identifiers_detected": latest_job.get("identifiers_detected", 0),
            "clinical_preservation": (
                f"FHIR {ci.get('fhir_bundles_checked', 0)} bundles OK"
                if fhir_ok and ci.get("fhir_bundles_checked", 0) > 0
                else ("FHIR_FAILED" if not fhir_ok else "NOT_MEASURED")
            ),
            "identity_precision": "NOT_MEASURED",
            "canary_status": "NOT_MEASURED",
            "critical_risks": critical_risks,
            "pending_checks": pending_checks,
        },
        "recent_jobs": recent_jobs,
        "recent_audits": recent_audits,
        "engine_status": {
            "state": "Operational & Armed",
            "mode": "Offline CPU-Only",
            "last_job_id": latest_job["id"],
            "last_job_duration": f"{latest_job.get('duration_secs', 0)}s",
        },
    }


# ==============================================================================
# 2. Organisations & Settings
# ==============================================================================


@app.get("/api/organisations")
def get_organisations() -> Dict[str, Any]:
    with get_db() as conn:
        orgs = [
            dict(row)
            for row in conn.execute(
                "SELECT * FROM organisations ORDER BY joined_at ASC"
            ).fetchall()
        ]
        for org in orgs:
            oid = org["id"]
            ds_cnt = conn.execute("SELECT COUNT(*) AS c FROM datasets WHERE org_id = ?", (oid,)).fetchone()["c"]
            job_cnt = conn.execute("SELECT COUNT(*) AS c FROM jobs WHERE org_id = ?", (oid,)).fetchone()["c"]
            rec_sum = conn.execute("SELECT COALESCE(SUM(records_processed), 0) AS s FROM jobs WHERE org_id = ?", (oid,)).fetchone()["s"]
            org["datasets_count"] = ds_cnt
            org["jobs_count"] = job_cnt
            org["records_contributed"] = rec_sum
    return {"organisations": orgs}


class OrgCreate(BaseModel):
    name: str
    org_type: str = "Hospital"
    region: str = "India"
    contact_role: str = "Privacy Officer"


class OrgUpdate(BaseModel):
    name: Optional[str] = None
    org_type: Optional[str] = None
    region: Optional[str] = None
    status: Optional[str] = None
    contact_role: Optional[str] = None


@app.post("/api/organisations")
def create_organisation(org: OrgCreate) -> Dict[str, Any]:
    if not org.name.strip():
        raise HTTPException(status_code=400, detail="Organisation name is required.")
    slug = re.sub(r"[^a-z0-9]+", "-", org.name.lower()).strip("-")[:20]
    org_id = f"org-{slug}-{os.urandom(2).hex()}"
    with get_db() as conn:
        conn.execute(
            "INSERT INTO organisations (id, name, org_type, region, status, records_contributed, joined_at, contact_role) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            (org_id, org.name.strip(), org.org_type.strip(), org.region.strip(), "Active", 0, time.time(), org.contact_role.strip()),
        )
    record_audit_event(
        event_type="ORGANISATION_CREATED",
        description=f"Registered synthetic organisation '{org.name.strip()}' ({org.org_type}).",
        org_id=org_id,
        resource_id=org_id,
        status="ACTIVE",
    )
    return {"status": "success", "org_id": org_id}


@app.patch("/api/organisations/{org_id}")
def update_organisation(org_id: str, update: OrgUpdate) -> Dict[str, Any]:
    with get_db() as conn:
        existing = conn.execute("SELECT * FROM organisations WHERE id = ?", (org_id,)).fetchone()
        if not existing:
            raise HTTPException(status_code=404, detail="Organisation not found")
        new_name = update.name.strip() if update.name else existing["name"]
        new_type = update.org_type.strip() if update.org_type else existing["org_type"]
        new_region = update.region.strip() if update.region else existing["region"]
        new_status = update.status.strip() if update.status else existing["status"]
        new_role = update.contact_role.strip() if update.contact_role else existing["contact_role"]
        conn.execute(
            "UPDATE organisations SET name = ?, org_type = ?, region = ?, status = ?, contact_role = ? WHERE id = ?",
            (new_name, new_type, new_region, new_status, new_role, org_id),
        )
    record_audit_event(
        event_type="ORGANISATION_UPDATED",
        description=f"Updated metadata for organisation {org_id}.",
        org_id=org_id,
        resource_id=org_id,
        status="UPDATED",
    )
    return {"status": "success", "org_id": org_id}


@app.get("/api/settings")
def get_settings() -> Dict[str, Any]:
    policy_path = STARTER_DIR / "config" / "policy.yaml"
    policy_text = policy_path.read_text(encoding="utf-8") if policy_path.exists() else ""
    params = load_policy_dict()

    secret_env = os.environ.get("RAKSHA_SECRET", "").strip()
    try:
        import raksha_engine.crypto as c_mod
        aes_avail = bool(getattr(c_mod, "HAS_CRYPTOGRAPHY", False))
    except Exception:
        aes_avail = False

    return {
        "policy_file": "starter/config/policy.yaml",
        "policy_content": policy_text,
        "parameters": {
            "date_shift_max_days": int(params.get("date_shift_max_days", 180)),
            "min_group_size": int(params.get("min_group_size", 5)),
            "age_band_width": int(params.get("age_band_width", 5)),
        },
        "security_status": {
            "raksha_secret_configured": bool(secret_env),
            "secret_source": "Environment (RAKSHA_SECRET)" if secret_env else "Console Fallback (Set RAKSHA_SECRET for production)",
            "encryption_at_rest": "AES-256-GCM / ChaCha20-Poly1305" if aes_avail else "HMAC-SHA256-CTR (Stdlib AEAD)",
            "offline_mode": True,
            "cpu_only": True,
            "max_upload_mb": 25,
            "retention_days": 30,
            "app_version": "1.0.0-m17",
        },
    }


class SettingsUpdate(BaseModel):
    date_shift_max_days: int = 180
    min_group_size: int = 5
    age_band_width: int = 5


@app.post("/api/settings")
def update_settings(update: SettingsUpdate) -> Dict[str, Any]:
    if not (1 <= update.date_shift_max_days <= 365):
        raise HTTPException(status_code=400, detail="date_shift_max_days must be between 1 and 365.")
    if not (2 <= update.min_group_size <= 50):
        raise HTTPException(status_code=400, detail="min_group_size must be between 2 and 50.")
    if not (1 <= update.age_band_width <= 20):
        raise HTTPException(status_code=400, detail="age_band_width must be between 1 and 20.")

    policy_path = STARTER_DIR / "config" / "policy.yaml"
    content = (
        f"# GuptKavach Policy Configuration\n"
        f"date_shift_max_days: {update.date_shift_max_days}\n"
        f"min_group_size: {update.min_group_size}\n"
        f"age_band_width: {update.age_band_width}\n"
    )
    policy_path.write_text(content, encoding="utf-8")

    record_audit_event(
        event_type="SETTINGS_UPDATED",
        description=f"Updated privacy policy parameters: date_shift={update.date_shift_max_days}, min_group={update.min_group_size}, age_band={update.age_band_width}.",
        resource_id="policy.yaml",
        status="UPDATED",
    )
    return {"status": "success", "message": "Policy settings updated and synchronized with engine."}


# ==============================================================================
# 3. Datasets & Privacy Gateway & Jobs Execution
# ==============================================================================


@app.get("/api/datasets")
def list_datasets(org_id: Optional[str] = Query(None)) -> Dict[str, Any]:
    datasets: List[Dict[str, Any]] = []

    # Include default practice benchmark when no org filter or explicitly requested
    practice_files = list(DEV_INPUT.rglob("*")) if DEV_INPUT.exists() else []
    practice_file_count = sum(1 for p in practice_files if p.is_file())
    datasets.append({
        "id": "practice-dev-dataset",
        "org_id": org_id or "org-hosp-a",
        "name": "Official Practice Benchmark Cohort",
        "source_type": "practice_benchmark",
        "files_count": practice_file_count,
        "formats": ["CSV", "TSV", "JSON", "TXT"],
        "validation_status": "VALIDATED",
        "is_default": True,
        "created_at": 0,
    })

    with get_db() as conn:
        if org_id:
            rows = conn.execute(
                "SELECT * FROM datasets WHERE org_id = ? ORDER BY created_at DESC",
                (org_id,),
            ).fetchall()
        else:
            rows = conn.execute("SELECT * FROM datasets ORDER BY created_at DESC").fetchall()

        for r in rows:
            d = dict(r)
            try:
                d["formats"] = json.loads(d.get("formats_json") or "[]")
            except Exception:
                d["formats"] = []
            try:
                d["validation_errors"] = json.loads(d.get("validation_errors_json") or "[]")
            except Exception:
                d["validation_errors"] = []
            d["is_default"] = False
            datasets.append(d)

    return {"datasets": datasets}


@app.post("/api/datasets/upload")
async def upload_dataset(
    org_id: str = Form(...),
    name: str = Form(...),
    files: List[UploadFile] = File(...),
) -> Dict[str, Any]:
    if not files or len(files) == 0:
        raise HTTPException(status_code=400, detail="At least one file is required.")

    with get_db() as conn:
        org_row = conn.execute("SELECT * FROM organisations WHERE id = ?", (org_id,)).fetchone()
        if not org_row:
            raise HTTPException(status_code=404, detail=f"Organisation '{org_id}' not found.")

    dataset_id = f"ds-{int(time.time())}-{os.urandom(3).hex()}"
    ds_dir = DATASETS_DIR / dataset_id
    ds_dir.mkdir(parents=True, exist_ok=True)

    validation_results: List[Dict[str, Any]] = []
    file_hashes: List[str] = []
    total_bytes = 0
    formats_found = set()
    valid_count = 0
    quarantine_candidate_count = 0

    for idx, uf in enumerate(files):
        raw_name = uf.filename or f"upload_{idx}.txt"
        safe_name = sanitize_filename(raw_name)
        content = await uf.read()
        vres = validate_uploaded_file(raw_name, content)

        if not vres["valid"] and not vres.get("quarantine_candidate"):
            # Unsafe path, empty batch, or exceeds size limit -> reject cleanly
            validation_results.append({"file_ref": f"file_{idx}", "valid": False, "reason": vres["reason"]})
            continue

        # Write to dataset staging directory (safe_name prevents traversal)
        dest = ds_dir / safe_name
        if dest.exists():
            dest = ds_dir / f"{dest.stem}_{idx}{dest.suffix}"
        dest.write_bytes(content)

        fhash = compute_bytes_sha256(content)
        file_hashes.append(fhash)
        total_bytes += len(content)
        formats_found.add(Path(safe_name).suffix.upper().lstrip(".") or "UNKNOWN")

        if vres["valid"]:
            valid_count += 1
        else:
            quarantine_candidate_count += 1
        validation_results.append({
            "file_ref": safe_name,
            "sha256": fhash,
            "valid": vres["valid"],
            "reason": vres.get("reason", "OK"),
        })

    if not file_hashes:
        raise HTTPException(status_code=400, detail="All uploaded files failed hard safety validation.")

    manifest_sha = compute_bytes_sha256(("|".join(sorted(file_hashes))).encode("utf-8"))

    # Prevent duplicate dataset registration for same organisation & identical content
    with get_db() as conn:
        dup = conn.execute(
            "SELECT id, name FROM datasets WHERE org_id = ? AND manifest_sha256 = ?",
            (org_id, manifest_sha),
        ).fetchone()
        if dup:
            raise HTTPException(
                status_code=409,
                detail=f"Duplicate dataset already registered for this organisation (dataset_id={dup['id']}).",
            )

        val_status = "VALIDATED" if quarantine_candidate_count == 0 else "VALIDATED_WITH_WARNINGS"
        conn.execute(
            """
            INSERT INTO datasets (
                id, org_id, name, source_type, storage_path, files_count, total_bytes,
                formats_json, manifest_sha256, validation_status, validation_errors_json, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                dataset_id,
                org_id,
                name.strip(),
                "uploaded_batch",
                str(ds_dir),
                len(file_hashes),
                total_bytes,
                json.dumps(sorted(formats_found)),
                manifest_sha,
                val_status,
                json.dumps(validation_results),
                time.time(),
            ),
        )

    record_audit_event(
        event_type="DATASET_UPLOAD_AND_VALIDATION",
        description=f"Registered dataset '{name.strip()}' ({len(file_hashes)} files: {valid_count} valid, {quarantine_candidate_count} quarantine-candidates).",
        org_id=org_id,
        resource_id=dataset_id,
        file_hash=manifest_sha,
        status=val_status,
        safe_metadata={"files_count": len(file_hashes), "valid": valid_count, "warnings": quarantine_candidate_count},
    )

    return {
        "status": "success",
        "dataset_id": dataset_id,
        "org_id": org_id,
        "validation_status": val_status,
        "files_count": len(file_hashes),
        "validation_results": validation_results,
    }


@app.get("/api/jobs")
def list_jobs(org_id: Optional[str] = Query(None)) -> Dict[str, Any]:
    with get_db() as conn:
        if org_id:
            rows = conn.execute("SELECT * FROM jobs WHERE org_id = ? ORDER BY created_at DESC LIMIT 50", (org_id,)).fetchall()
        else:
            rows = conn.execute("SELECT * FROM jobs ORDER BY created_at DESC LIMIT 50").fetchall()
    return {"jobs": [dict(r) for r in rows]}


@app.post("/api/jobs")
async def create_job(
    dataset_id: str = Form("practice-dev-dataset"),
    org_id: str = Form("org-hosp-a"),
    files: Optional[List[UploadFile]] = File(None),
) -> Dict[str, Any]:
    # Verify org exists
    with get_db() as conn:
        org_row = conn.execute("SELECT * FROM organisations WHERE id = ?", (org_id,)).fetchone()
        if not org_row:
            raise HTTPException(status_code=404, detail=f"Organisation '{org_id}' not found.")

    job_id = f"job-{int(time.time())}-{os.urandom(3).hex()}"
    job_dir = JOBS_DIR / job_id
    job_input = job_dir / "input"
    job_output = job_dir / "output"
    job_input.mkdir(parents=True, exist_ok=True)
    job_output.mkdir(parents=True, exist_ok=True)

    stage_history: List[Dict[str, Any]] = []
    input_source_desc = ""

    # Resolve input source cleanly
    if files and len(files) > 0 and files[0].filename:
        input_source_desc = f"Uploaded Batch ({len(files)} files)"
        for idx, file in enumerate(files):
            safe_name = sanitize_filename(file.filename or f"upload_{idx}.txt")
            dest = job_input / safe_name
            content = await file.read()
            dest.write_bytes(content)
    elif dataset_id == "practice-dev-dataset":
        input_source_desc = "Official Practice Benchmark Cohort"
        job_input = DEV_INPUT
    else:
        with get_db() as conn:
            ds_row = conn.execute("SELECT * FROM datasets WHERE id = ?", (dataset_id,)).fetchone()
        if not ds_row or not Path(ds_row["storage_path"]).is_dir():
            raise HTTPException(status_code=404, detail=f"Dataset '{dataset_id}' not found on disk.")
        if ds_row["org_id"] != org_id:
            raise HTTPException(status_code=403, detail="Dataset belongs to a different organisation.")
        job_input = Path(ds_row["storage_path"])
        input_source_desc = ds_row["name"]

    stage_history.append({"stage": "INPUT_STAGED", "timestamp": time.time(), "status": "OK"})
    record_audit_event(
        event_type="PROCESSING_STARTED",
        description=f"Started privacy pipeline job {job_id} for dataset {dataset_id}.",
        org_id=org_id,
        resource_id=dataset_id,
        job_id=job_id,
        status="RUNNING",
    )

    # Execute the real Python privacy engine!
    result = execute_engine(input_dir=job_input, output_dir=job_output)
    stage_history.append({"stage": "PRIVACY_ENGINE_EXECUTED", "timestamp": time.time(), "status": "OK" if result["success"] else "FAILED"})

    # Run attack simulation against actual sanitized output
    attack_res = run_attack_simulation_for_job(job_output) if result["success"] else {"status": "NOT_RUN", "vectors": []}
    attack_id = f"atk-{job_id}"
    stage_history.append({"stage": "ATTACK_SIMULATION_COMPLETED", "timestamp": time.time(), "status": attack_res["status"]})

    # Verify generated Privacy Passport
    passport_data = result.get("passport") or {}
    passport_id = passport_data.get("certificate_identity", {}).get("certificate_id") or f"PASS-{job_id}"
    passport_ver = verify_passport_for_job(job_output) if passport_data else {"status": "NOT_FOUND", "valid": False}
    stage_history.append({"stage": "PASSPORT_VERIFIED", "timestamp": time.time(), "status": passport_ver["status"]})

    # Determine authoritative release decision
    gate_status = (result.get("release_gate") or {}).get("status", "BLOCKED")
    fhir_ok = (result.get("clinical_integrity") or {}).get("fhir_validation_passed", True)
    if not result["success"] or result["files_sanitized"] == 0:
        release_decision = "BLOCKED"
    elif gate_status == "BLOCKED" or not fhir_ok or not passport_ver.get("valid", False):
        release_decision = "BLOCKED"
    elif gate_status == "REVIEW_REQUIRED" or attack_res.get("post_uniquely_distinguishable", 0) > 0:
        release_decision = "REVIEW_REQUIRED"
    else:
        release_decision = "APPROVED"

    job_status = "Completed" if result["success"] else "Failed"
    policy_ver = str((result.get("release_gate") or {}).get("policy_version", "1.0"))
    safe_err = sanitize_log_text(result["stderr"]) if not result["success"] else None

    with get_db() as conn:
        conn.execute(
            """
            INSERT INTO jobs (
                id, dataset_id, org_id, created_at, status, current_stage, stage_history_json,
                input_name, output_dir, files_total, files_sanitized, files_quarantined,
                records_processed, records_linked, identifiers_detected, records_generalized,
                records_suppressed, duration_secs, policy_version, privacy_assessment_ref,
                clinical_assessment_ref, identity_assessment_ref, attack_assessment_ref,
                passport_id, release_decision, error_msg
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                job_id,
                dataset_id,
                org_id,
                time.time(),
                job_status,
                "COMPLETED" if result["success"] else "FAILED",
                json.dumps(stage_history),
                input_source_desc,
                str(job_output),
                result["files_total"],
                result["files_sanitized"],
                result["files_quarantined"],
                result["records_processed"],
                result["records_linked"],
                result["identifiers_detected"],
                result["records_generalized"],
                result["records_suppressed"],
                result["duration_secs"],
                policy_ver,
                f"priv-{job_id}",
                f"clin-{job_id}",
                f"ident-{job_id}",
                attack_id,
                passport_id,
                release_decision,
                safe_err,
            ),
        )

        # Persist attack simulation
        conn.execute(
            """
            INSERT INTO attack_simulations (
                id, job_id, org_id, dataset_id, executed_at, total_records,
                pre_uniquely_distinguishable, post_uniquely_distinguishable, vectors_json
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                attack_id,
                job_id,
                org_id,
                dataset_id,
                time.time(),
                attack_res.get("total_records", 0),
                int(attack_res.get("pre_uniquely_distinguishable", 0) or 0) if isinstance(attack_res.get("pre_uniquely_distinguishable"), int) else 0,
                int(attack_res.get("post_uniquely_distinguishable", 0) or 0),
                json.dumps(attack_res.get("vectors", [])),
            ),
        )

        # Persist passport
        if passport_data:
            dp = passport_data.get("dataset_provenance", {})
            sig = passport_data.get("signature", {})
            conn.execute(
                """
                INSERT OR REPLACE INTO passports (
                    passport_id, job_id, dataset_id, org_id, policy_version,
                    input_manifest_hash, output_manifest_hash, generated_at,
                    release_decision, signature_status, verification_status, passport_json
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    passport_id,
                    job_id,
                    dataset_id,
                    org_id,
                    policy_ver,
                    dp.get("input_fingerprint", ""),
                    dp.get("output_manifest_root_hash", ""),
                    passport_data.get("certificate_identity", {}).get("issued_at", ""),
                    release_decision,
                    sig.get("status", "UNSIGNED"),
                    passport_ver.get("status", "UNVERIFIED"),
                    json.dumps(passport_data),
                ),
            )

    report_hash = compute_file_sha256(job_output / "report.json") if (job_output / "report.json").exists() else "N/A"
    record_audit_event(
        event_type="PROCESSING_COMPLETED",
        description=f"Job {job_id} finished ({result['files_sanitized']} sanitized, {result['files_quarantined']} quarantined). Release decision: {release_decision}.",
        org_id=org_id,
        resource_id=dataset_id,
        job_id=job_id,
        file_hash=report_hash,
        policy_version=policy_ver,
        status=release_decision,
    )
    if result["files_quarantined"] > 0:
        record_audit_event(
            event_type="QUARANTINE_ENFORCED",
            description=f"Quarantined {result['files_quarantined']} unsafe/unparseable files in job {job_id}; 0 raw bytes exported.",
            org_id=org_id,
            resource_id=dataset_id,
            job_id=job_id,
            status="QUARANTINED",
        )

    return {
        "job_id": job_id,
        "org_id": org_id,
        "dataset_id": dataset_id,
        "status": job_status,
        "release_decision": release_decision,
        "passport_id": passport_id,
        "result": {
            "files_total": result["files_total"],
            "files_sanitized": result["files_sanitized"],
            "files_quarantined": result["files_quarantined"],
            "records_processed": result["records_processed"],
            "records_linked": result["records_linked"],
            "identifiers_detected": result["identifiers_detected"],
            "duration_secs": result["duration_secs"],
            "files_report": result["files_report"],
            "release_gate": result["release_gate"],
        },
    }


@app.get("/api/jobs/{job_id}")
def get_job(job_id: str) -> Dict[str, Any]:
    job = _resolve_job_row(job_id=job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    out_dir = _job_output_path(job)
    report_data = read_job_report(out_dir) if out_dir else {}
    job["files_report"] = report_data.get("files", [])
    job["privacy_intelligence"] = report_data.get("privacy_intelligence", {})
    job["clinical_integrity"] = report_data.get("clinical_integrity", {})
    try:
        job["stage_history"] = json.loads(job.get("stage_history_json") or "[]")
    except Exception:
        job["stage_history"] = []
    return {"job": job}


class ReleaseDecisionUpdate(BaseModel):
    decision: str  # APPROVED | REJECTED
    reason: str = ""


@app.post("/api/jobs/{job_id}/release")
def update_job_release(job_id: str, body: ReleaseDecisionUpdate) -> Dict[str, Any]:
    job = _resolve_job_row(job_id=job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    dec = body.decision.upper()
    if dec not in ("APPROVED", "REJECTED"):
        raise HTTPException(status_code=400, detail="Decision must be APPROVED or REJECTED.")
    if dec == "APPROVED" and (job["files_sanitized"] == 0 or job["status"] != "Completed"):
        raise HTTPException(status_code=400, detail="Cannot approve a failed job or a job with 0 sanitized files.")

    new_dec = "APPROVED" if dec == "APPROVED" else "BLOCKED"
    with get_db() as conn:
        conn.execute("UPDATE jobs SET release_decision = ? WHERE id = ?", (new_dec, job_id))
        conn.execute("UPDATE passports SET release_decision = ? WHERE job_id = ?", (new_dec, job_id))

    record_audit_event(
        event_type="RELEASE_APPROVED" if dec == "APPROVED" else "RELEASE_REJECTED",
        description=f"Privacy Officer set release decision to {new_dec} for job {job_id}. {sanitize_log_text(body.reason)}",
        org_id=job.get("org_id"),
        resource_id=job.get("dataset_id"),
        job_id=job_id,
        status=new_dec,
    )
    return {"status": "success", "job_id": job_id, "release_decision": new_dec}


@app.get("/api/jobs/{job_id}/download")
def download_job_outputs(job_id: str):
    """Safely zips and returns valid sanitized outputs ONLY when release is permitted."""
    job = _resolve_job_row(job_id=job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    if job.get("release_decision") not in ("APPROVED", "APPROVED_WITH_WARNINGS"):
        raise HTTPException(
            status_code=403,
            detail=f"Download blocked: release_decision is '{job.get('release_decision')}'. Must be APPROVED.",
        )

    out_dir = _job_output_path(job)
    if not out_dir or not (out_dir / "sanitized").is_dir():
        raise HTTPException(status_code=404, detail="Sanitized output directory not found for this job.")

    sanitized_dir = out_dir / "sanitized"
    zip_buffer = io.BytesIO()
    with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zf:
        for root, _, files in os.walk(str(sanitized_dir)):
            for f in files:
                file_path = Path(root) / f
                arcname = file_path.relative_to(sanitized_dir).as_posix()
                zf.write(file_path, f"sanitized/{arcname}")

        for artifact in ("report.json", "records.jsonl", "dataset_manifest.json", "privacy_passport.json", "privacy_passport.html"):
            art_path = out_dir / artifact
            if art_path.is_file():
                zf.write(art_path, artifact)

    record_audit_event(
        event_type="BUNDLE_DOWNLOAD",
        description=f"Exported sanitized release bundle for job {job_id}.",
        org_id=job.get("org_id"),
        resource_id=job.get("dataset_id"),
        job_id=job_id,
        status="DOWNLOADED",
    )

    zip_buffer.seek(0)
    return StreamingResponse(
        zip_buffer,
        media_type="application/zip",
        headers={"Content-Disposition": f"attachment; filename=MediLocker_Protected_{job_id}.zip"},
    )


# ==============================================================================
# 4. Identity Continuity, Clinical Integrity, Privacy Intelligence, Attack Lab
# ==============================================================================


@app.get("/api/identity-graph")
def get_identity_graph(
    org_id: Optional[str] = Query(None),
    dataset_id: Optional[str] = Query(None),
    job_id: Optional[str] = Query(None),
) -> Dict[str, Any]:
    job = _resolve_job_row(job_id=job_id, org_id=org_id, dataset_id=dataset_id)
    out_dir = _job_output_path(job)
    res = parse_identity_continuity_graph(out_dir)
    res["job_id"] = job["id"] if job else None
    res["org_id"] = job["org_id"] if job else org_id
    return res


@app.get("/api/clinical-integrity")
def get_clinical_integrity(
    org_id: Optional[str] = Query(None),
    job_id: Optional[str] = Query(None),
) -> Dict[str, Any]:
    job = _resolve_job_row(job_id=job_id, org_id=org_id)
    out_dir = _job_output_path(job)
    if not out_dir:
        return {"status": "NOT_RUN", "job_id": None, "org_id": org_id}
    res = evaluate_clinical_integrity_for_job(out_dir)
    res["job_id"] = job["id"]
    res["org_id"] = job["org_id"]
    return res


@app.get("/api/privacy-intelligence")
def get_privacy_intelligence(
    org_id: Optional[str] = Query(None),
    job_id: Optional[str] = Query(None),
) -> Dict[str, Any]:
    job = _resolve_job_row(job_id=job_id, org_id=org_id)
    out_dir = _job_output_path(job)
    if not job or not out_dir:
        return {"status": "NOT_RUN", "job_id": None, "org_id": org_id}

    report = read_job_report(out_dir)
    pi = report.get("privacy_intelligence", {})
    counts = report.get("counts", {})
    risk_sum = pi.get("risk_summary", {})
    gate = pi.get("release_gate", {})

    total_recs = counts.get("records_processed", 0)
    below_min = risk_sum.get("records_below_min_group_post", 0)
    uniqueness_pct = round((below_min / total_recs) * 100, 2) if total_recs > 0 else "NOT_MEASURED"

    return {
        "status": "MEASURED",
        "job_id": job["id"],
        "org_id": job["org_id"],
        "policy_version": pi.get("policy_version", "1.0"),
        "release_gate": gate,
        "measured_metrics": {
            "identifiers_detected": counts.get("identifiers_detected", 0),
            "records_processed": total_recs,
            "records_generalized": counts.get("records_generalized", 0),
            "records_suppressed": counts.get("records_suppressed", 0),
            "unique_candidate_groups": risk_sum.get("unique_candidate_groups_post", 0),
            "records_below_min_group_pre": risk_sum.get("records_below_min_group_pre", 0),
            "records_below_min_group_post": below_min,
            "rare_group_rate_pct": uniqueness_pct,
        },
        "ground_truth_metrics": {
            "direct_identifier_leakage": "NOT_MEASURED",
            "residual_pii_leakage": "NOT_MEASURED",
            "canary_leakage": "NOT_MEASURED",
            "note": "Ground-truth leakage rates require labelled adversarial test corpus (evaluated in offline test suite).",
        },
        "risk_summary": risk_sum,
        "mitigation_actions": pi.get("mitigation_actions", {}),
        "field_tier_counts": pi.get("field_tier_counts", {}),
        "stage_trace": pi.get("stage_trace", []),
    }


@app.get("/api/attacks")
def get_attacks(
    org_id: Optional[str] = Query(None),
    job_id: Optional[str] = Query(None),
) -> Dict[str, Any]:
    job = _resolve_job_row(job_id=job_id, org_id=org_id)
    if not job:
        not_run_vectors = [
            {
                "strategy": strat,
                "label": meta["label"],
                "quasi_identifiers": meta["quasi_identifiers"],
                "algorithm": meta["algorithm"],
                "status": "NOT_RUN",
                "records_tested": 0,
                "records_at_risk_before": "NOT_MEASURED",
                "records_at_risk_after": "NOT_MEASURED",
                "mitigation_applied": "N/A",
                "residual_risk_pct": "NOT_RUN",
                "executed_at": None,
            }
            for strat, meta in ATTACK_VECTOR_META.items()
        ]
        return {"status": "NOT_RUN", "job_id": None, "vectors": not_run_vectors}

    with get_db() as conn:
        row = conn.execute(
            "SELECT * FROM attack_simulations WHERE job_id = ? ORDER BY executed_at DESC LIMIT 1",
            (job["id"],),
        ).fetchone()

    if not row:
        return {"status": "NOT_RUN", "job_id": job["id"], "vectors": []}

    vectors = json.loads(row["vectors_json"] or "[]")
    total_rec = row["total_records"]
    post_uniq = row["post_uniquely_distinguishable"]
    res_pct = round((post_uniq / total_rec) * 100, 2) if total_rec > 0 else "NOT_TESTED"
    blocked = sum(1 for v in vectors if v.get("status") == "BLOCKED")

    return {
        "status": "EXECUTED" if total_rec > 0 else "NOT_TESTED",
        "simulation_id": row["id"],
        "job_id": job["id"],
        "org_id": job["org_id"],
        "executed_at": row["executed_at"],
        "total_records": total_rec,
        "pre_uniquely_distinguishable": row["pre_uniquely_distinguishable"],
        "post_uniquely_distinguishable": post_uniq,
        "residual_uniqueness_pct": res_pct,
        "vectors_blocked": blocked,
        "vectors_total": len(vectors),
        "vectors": vectors,
    }


class AttackRunRequest(BaseModel):
    job_id: str


@app.post("/api/attacks/run")
def run_attacks_endpoint(req: AttackRunRequest) -> Dict[str, Any]:
    job = _resolve_job_row(job_id=req.job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    out_dir = _job_output_path(job)
    if not out_dir:
        raise HTTPException(status_code=404, detail="Job output directory missing")

    res = run_attack_simulation_for_job(out_dir)
    sim_id = f"atk-{job['id']}-{int(time.time())}"
    with get_db() as conn:
        conn.execute(
            """
            INSERT INTO attack_simulations (
                id, job_id, org_id, dataset_id, executed_at, total_records,
                pre_uniquely_distinguishable, post_uniquely_distinguishable, vectors_json
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                sim_id,
                job["id"],
                job["org_id"],
                job["dataset_id"],
                time.time(),
                res.get("total_records", 0),
                int(res.get("pre_uniquely_distinguishable", 0) or 0) if isinstance(res.get("pre_uniquely_distinguishable"), int) else 0,
                int(res.get("post_uniquely_distinguishable", 0) or 0),
                json.dumps(res.get("vectors", [])),
            ),
        )

    record_audit_event(
        event_type="ATTACK_SIMULATION",
        description=f"Executed 7-vector attack simulation on sanitized output of job {job['id']}. Residual uniqueness: {res.get('residual_uniqueness_pct')}%.",
        org_id=job.get("org_id"),
        resource_id=job.get("dataset_id"),
        job_id=job["id"],
        status=res.get("status", "EXECUTED"),
    )
    return {"simulation_id": sim_id, "job_id": job["id"], **res}


@app.get("/api/threat-lab")
def get_threat_lab(
    org_id: Optional[str] = Query(None),
    job_id: Optional[str] = Query(None),
) -> Dict[str, Any]:
    attacks = get_attacks(org_id=org_id, job_id=job_id)
    job = _resolve_job_row(job_id=job_id, org_id=org_id)
    out_dir = _job_output_path(job)
    report = read_job_report(out_dir) if out_dir else {}
    return {
        "job_id": job["id"] if job else None,
        "org_id": job["org_id"] if job else org_id,
        "attack_simulation": attacks,
        "files_report": report.get("files", []),
        "clinical_integrity": report.get("clinical_integrity", {}),
        "canary_status": "NOT_MEASURED",
    }


# ==============================================================================
# 5. Privacy Passports
# ==============================================================================


@app.get("/api/passports")
def list_passports(org_id: Optional[str] = Query(None)) -> Dict[str, Any]:
    with get_db() as conn:
        if org_id:
            rows = conn.execute(
                "SELECT passport_id, job_id, dataset_id, org_id, policy_version, input_manifest_hash, output_manifest_hash, generated_at, release_decision, signature_status, verification_status FROM passports WHERE org_id = ? ORDER BY generated_at DESC",
                (org_id,),
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT passport_id, job_id, dataset_id, org_id, policy_version, input_manifest_hash, output_manifest_hash, generated_at, release_decision, signature_status, verification_status FROM passports ORDER BY generated_at DESC"
            ).fetchall()
    return {"passports": [dict(r) for r in rows]}


@app.get("/api/passports/{job_id}")
def get_passport(job_id: str) -> Dict[str, Any]:
    with get_db() as conn:
        row = conn.execute("SELECT * FROM passports WHERE job_id = ?", (job_id,)).fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Privacy Passport not found for this job")
    data = dict(row)
    try:
        data["passport"] = json.loads(data.pop("passport_json"))
    except Exception:
        data["passport"] = {}
    data["disclaimer"] = "Generated technical evidence artifact for local release governance; not an external regulatory certification."
    return data


@app.post("/api/passports/{job_id}/verify")
def verify_passport_endpoint(job_id: str) -> Dict[str, Any]:
    job = _resolve_job_row(job_id=job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    out_dir = _job_output_path(job)
    if not out_dir:
        raise HTTPException(status_code=404, detail="Job output directory missing")

    ver = verify_passport_for_job(out_dir)
    with get_db() as conn:
        conn.execute(
            "UPDATE passports SET verification_status = ? WHERE job_id = ?",
            (ver.get("status", "UNVERIFIED"), job_id),
        )
    record_audit_event(
        event_type="PASSPORT_VERIFIED",
        description=f"Verified Privacy Passport integrity for job {job_id}: status={ver.get('status')}.",
        org_id=job.get("org_id"),
        resource_id=job.get("passport_id"),
        job_id=job_id,
        status=ver.get("status", "UNVERIFIED"),
    )
    return {"job_id": job_id, **ver}


# ==============================================================================
# 6. Research Collaboration & Trust / Audit
# ==============================================================================


@app.get("/api/research/requests")
def list_research_requests() -> Dict[str, Any]:
    with get_db() as conn:
        requests = [
            dict(row)
            for row in conn.execute(
                "SELECT * FROM research_requests ORDER BY created_at DESC"
            ).fetchall()
        ]
        for r in requests:
            for field in ("target_orgs", "datasets_requested"):
                try:
                    r[field] = json.loads(r[field]) if r.get(field) else []
                except Exception:
                    pass
    return {"requests": requests}


class NewResearchRequest(BaseModel):
    title: str
    requestor_org: str
    target_orgs: List[str]
    dataset_id: str = "practice-dev-dataset"
    purpose: str
    datasets_requested: List[str] = []


@app.post("/api/research/requests")
def create_research_request(req: NewResearchRequest) -> Dict[str, Any]:
    if not req.title.strip() or not req.purpose.strip():
        raise HTTPException(status_code=400, detail="Title and purpose are required.")
    req_id = f"req-{int(time.time())}-{os.urandom(2).hex()}"
    with get_db() as conn:
        conn.execute(
            """
            INSERT INTO research_requests (
                id, title, requestor_org, target_orgs, dataset_id, job_id, purpose,
                status, created_at, reviewed_at, reviewed_by, datasets_requested,
                permitted_output_ref, release_simulated
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                req_id,
                req.title.strip(),
                req.requestor_org.strip(),
                json.dumps(req.target_orgs),
                req.dataset_id,
                None,
                req.purpose.strip(),
                "Pending",
                time.time(),
                None,
                None,
                json.dumps(req.datasets_requested or [req.dataset_id]),
                None,
                0,
            ),
        )
    record_audit_event(
        event_type="RESEARCH_REQUEST_CREATED",
        description=f"Synthetic research request '{req.title.strip()}' submitted by {req.requestor_org.strip()}.",
        resource_id=req_id,
        status="PENDING",
    )
    return {"status": "success", "request_id": req_id}


@app.post("/api/research/requests/{req_id}/approve")
def approve_request(req_id: str) -> Dict[str, Any]:
    with get_db() as conn:
        req_row = conn.execute("SELECT * FROM research_requests WHERE id = ?", (req_id,)).fetchone()
        if not req_row:
            raise HTTPException(status_code=404, detail="Research request not found")

        ds_id = req_row["dataset_id"] or "practice-dev-dataset"
        approved_job = conn.execute(
            "SELECT id, org_id FROM jobs WHERE dataset_id = ? AND release_decision = 'APPROVED' ORDER BY created_at DESC LIMIT 1",
            (ds_id,),
        ).fetchone()
        if not approved_job:
            # Check any approved job as fallback for demo cohort
            approved_job = conn.execute(
                "SELECT id, org_id FROM jobs WHERE release_decision = 'APPROVED' ORDER BY created_at DESC LIMIT 1"
            ).fetchone()

        if not approved_job:
            raise HTTPException(
                status_code=400,
                detail="Cannot approve research release: no APPROVED sanitized job exists yet for the requested dataset.",
            )

        out_ref = f"/api/jobs/{approved_job['id']}/download"
        conn.execute(
            "UPDATE research_requests SET status = 'Approved', reviewed_at = ?, reviewed_by = 'local-privacy-officer', job_id = ?, permitted_output_ref = ?, release_simulated = 1 WHERE id = ?",
            (time.time(), approved_job["id"], out_ref, req_id),
        )

    record_audit_event(
        event_type="RESEARCH_REQUEST_APPROVED",
        description=f"Approved research request {req_id} linked to sanitized job {approved_job['id']}.",
        org_id=approved_job["org_id"],
        resource_id=req_id,
        job_id=approved_job["id"],
        status="APPROVED",
    )
    return {"status": "success", "message": f"Request {req_id} approved", "permitted_output_ref": out_ref, "job_id": approved_job["id"]}


@app.post("/api/research/requests/{req_id}/reject")
def reject_request(req_id: str) -> Dict[str, Any]:
    with get_db() as conn:
        req_row = conn.execute("SELECT * FROM research_requests WHERE id = ?", (req_id,)).fetchone()
        if not req_row:
            raise HTTPException(status_code=404, detail="Research request not found")
        conn.execute(
            "UPDATE research_requests SET status = 'Rejected', reviewed_at = ?, reviewed_by = 'local-privacy-officer' WHERE id = ?",
            (time.time(), req_id),
        )
    record_audit_event(
        event_type="RESEARCH_REQUEST_REJECTED",
        description=f"Rejected research request {req_id}.",
        resource_id=req_id,
        status="REJECTED",
    )
    return {"status": "success", "message": f"Request {req_id} rejected"}


@app.get("/api/audit")
def get_audit_trail(
    org_id: Optional[str] = Query(None),
    event_type: Optional[str] = Query(None),
    limit: int = Query(100, ge=1, le=500),
) -> Dict[str, Any]:
    clauses = []
    params: List[Any] = []
    if org_id:
        clauses.append("org_id = ?")
        params.append(org_id)
    if event_type:
        clauses.append("event_type = ?")
        params.append(event_type)
    where_sql = ("WHERE " + " AND ".join(clauses)) if clauses else ""
    params.append(limit)

    with get_db() as conn:
        logs = [
            dict(row)
            for row in conn.execute(
                f"SELECT * FROM audit_logs {where_sql} ORDER BY timestamp DESC LIMIT ?",
                tuple(params),
            ).fetchall()
        ]
    return {
        "audit_logs": logs,
        "append_only": True,
        "confidentiality_guarantee": "Zero raw PII and Zero secrets in logs",
    }
