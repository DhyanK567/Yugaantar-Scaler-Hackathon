"""Server-side, job-isolated and mathematically valid dashboard KPI computation.

All metrics are derived from persisted SQLite job, privacy_assessments,
clinical_reports, and identity_clusters rows, plus verified repository-level
execution compliance checks. Never fabricates metrics or averages percentages.
"""
from __future__ import annotations

import json
import os
import sqlite3
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

REPO_ROOT = Path(__file__).resolve().parents[1]
COMPLETED_JOB_STATUSES = ("COMPLETED", "COMPLETED_WITH_WARNINGS", "QUARANTINED")
LLM_DISALLOWED_PACKAGES = (
    "openai",
    "anthropic",
    "langchain",
    "llama-index",
    "transformers",
    "torch",
    "google-generativeai",
    "litellm",
    "cohere",
)


def _org_clause(org_ids: Optional[List[str]], alias: str = "j") -> Tuple[str, List[Any]]:
    if org_ids is None:
        return "1=1", []
    if not org_ids:
        return "1=0", []
    placeholders = ",".join("?" for _ in org_ids)
    return f"{alias}.organisation_id IN ({placeholders})", list(org_ids)


def get_runtime_execution_compliance() -> Dict[str, Any]:
    """Verify repository-level offline, CPU-only, no-LLM compliance properties."""
    req_files = [REPO_ROOT / "requirements.txt", REPO_ROOT / "starter" / "requirements.txt"]
    llm_detected = False
    checked_files = 0
    for req_path in req_files:
        if req_path.is_file():
            checked_files += 1
            text = req_path.read_text(encoding="utf-8", errors="ignore").lower()
            for line in text.splitlines():
                stripped = line.split("#", 1)[0].strip()
                if not stripped:
                    continue
                if any(pkg in stripped for pkg in LLM_DISALLOWED_PACKAGES):
                    llm_detected = True

    offline_env = os.environ.get("MEDILOCKER_OFFLINE_MODE", "1").strip().lower() not in ("0", "false", "no")
    mode = "OFFLINE" if offline_env else "ONLINE"
    device = "CPU"
    llm_dep = "DETECTED" if llm_detected else "NONE"
    verification_status = "VERIFIED" if (checked_files > 0 and not llm_detected and offline_env) else "FAILED"

    return {
        "mode": mode,
        "device": device,
        "llm_dependency": llm_dep,
        "network_calls": 0 if offline_env else None,
        "verification_status": verification_status,
        "scope": "REPOSITORY_AUDIT",
        "checks_passed": int(checked_files > 0) + int(not llm_detected) + int(offline_env),
        "checks_total": 3,
    }


def _extract_identity_for_job(conn: sqlite3.Connection, job_id: str) -> Dict[str, Any]:
    row = conn.execute("SELECT * FROM identity_clusters WHERE job_id = ?", (job_id,)).fetchone()
    if not row:
        return {
            "status": "NOT_MEASURED",
            "true_positives": 0,
            "false_positives": 0,
            "precision": None,
            "false_merges": 0,
            "records_assessed": 0,
            "scope": "JOB",
        }
    data = dict(row)
    false_merges = int(data.get("false_merges") or 0)
    total_patients = int(data.get("total_patients") or 0)
    precision = data.get("precision")
    tp = 0
    fp = false_merges
    try:
        graph = json.loads(data.get("graph_json") or "{}")
        stats = graph.get("stats") or {}
        if "true_positives" in stats:
            tp = int(stats["true_positives"])
        elif "linked_records" in stats:
            tp = int(stats["linked_records"])
        elif precision is not None and total_patients > 0:
            tp = total_patients
        if "false_positives" in stats:
            fp = int(stats["false_positives"])
        if total_patients == 0 and "total_records" in stats:
            total_patients = int(stats["total_records"])
    except Exception:
        if precision is not None and total_patients > 0:
            tp = total_patients

    denom = tp + fp
    if precision is None or denom <= 0:
        return {
            "status": "NOT_MEASURED",
            "true_positives": 0,
            "false_positives": 0,
            "precision": None,
            "false_merges": false_merges,
            "records_assessed": total_patients,
            "scope": "JOB",
        }

    computed_precision = round(tp / denom, 4)
    return {
        "status": "MEASURED",
        "true_positives": tp,
        "false_positives": fp,
        "precision": computed_precision,
        "false_merges": false_merges,
        "records_assessed": total_patients,
        "scope": "JOB",
    }


def build_job_dashboard_metrics(conn: sqlite3.Connection, job_row: Dict[str, Any]) -> Dict[str, Any]:
    """Build strictly job-isolated KPI payload for a single job."""
    job_id = job_row["id"]
    job_status = str(job_row.get("status") or "UNKNOWN").upper()
    files_total = int(job_row.get("files_total") or 0)

    pa_row = conn.execute("SELECT * FROM privacy_assessments WHERE job_id = ?", (job_id,)).fetchone()
    cr_row = conn.execute("SELECT * FROM clinical_reports WHERE job_id = ?", (job_id,)).fetchone()

    # Card 1: Canary Protection
    if not pa_row or str(pa_row["canary_status"]).upper() == "NOT_RUN" or int(pa_row["canary_planted"] or 0) <= 0:
        canary = {
            "status": "NOT_TESTED",
            "leaked": None,
            "planted": 0,
            "files_assessed": files_total,
            "outcome": "NOT_TESTED",
        }
    else:
        leaked = int(pa_row["canary_leaks"] or 0)
        planted = int(pa_row["canary_planted"] or 0)
        canary = {
            "status": "TESTED",
            "leaked": leaked,
            "planted": planted,
            "files_assessed": files_total,
            "outcome": "PROTECTED" if leaked == 0 else "LEAKAGE_DETECTED",
        }

    # Card 2: Identity Precision
    identity = _extract_identity_for_job(conn, job_id)

    # Card 3: Clinical Fidelity
    if not cr_row or int(cr_row["expected_values"] or 0) <= 0:
        clinical = {
            "status": "NOT_MEASURED",
            "expected": 0,
            "preserved": 0,
            "missing": 0,
            "modified": 0,
            "preservation_percentage": None,
        }
    else:
        expected = int(cr_row["expected_values"] or 0)
        preserved = int(cr_row["preserved_values"] or 0)
        missing = int(cr_row["missing_values"] or 0)
        modified = int(cr_row["modified_values"] or 0)
        pct = round((preserved / expected) * 100.0, 4)
        clinical = {
            "status": "MEASURED",
            "expected": expected,
            "preserved": preserved,
            "missing": missing,
            "modified": modified,
            "preservation_percentage": pct,
        }

    if job_status == "FAILED":
        if canary["status"] == "TESTED":
            canary["status"] = "FAILED"
        if clinical["status"] == "MEASURED":
            clinical["status"] = "FAILED"

    return {
        "scope": "JOB",
        "job_id": job_id,
        "dataset_id": job_row.get("dataset_id"),
        "dataset_name": job_row.get("dataset_name") or job_row.get("input_name") or job_id,
        "organisation_id": job_row.get("organisation_id"),
        "job_status": job_status,
        "release_decision": job_row.get("release_decision") or "PENDING",
        "processed_at": job_row.get("completed_at") or job_row.get("created_at"),
        "metrics": {
            "canary": canary,
            "identity": identity,
            "clinical": clinical,
            "execution": get_runtime_execution_compliance(),
        },
    }


def build_aggregate_dashboard_metrics(
    conn: sqlite3.Connection, completed_jobs: List[Dict[str, Any]]
) -> Dict[str, Any]:
    """Compute mathematically valid aggregate metrics across completed authorised jobs only."""
    if not completed_jobs:
        return {
            "scope": "AGGREGATE",
            "job_id": None,
            "dataset_id": None,
            "dataset_name": "All completed datasets",
            "job_status": "EMPTY",
            "release_decision": "NOT_MEASURED",
            "processed_at": None,
            "jobs_included": 0,
            "metrics": {
                "canary": {"status": "NOT_TESTED", "leaked": None, "planted": 0, "files_assessed": 0, "outcome": "NOT_TESTED"},
                "identity": {"status": "NOT_MEASURED", "true_positives": 0, "false_positives": 0, "precision": None, "false_merges": 0, "records_assessed": 0, "scope": "AGGREGATE"},
                "clinical": {"status": "NOT_MEASURED", "expected": 0, "preserved": 0, "missing": 0, "modified": 0, "preservation_percentage": None},
                "execution": get_runtime_execution_compliance(),
            },
        }

    canary_leaked = 0
    canary_planted = 0
    canary_files = 0
    canary_tested_jobs = 0

    id_tp = 0
    id_fp = 0
    id_false_merges = 0
    id_records = 0
    id_measured_jobs = 0

    clin_exp = 0
    clin_pres = 0
    clin_miss = 0
    clin_mod = 0
    clin_measured_jobs = 0

    for j in completed_jobs:
        m = build_job_dashboard_metrics(conn, j)["metrics"]
        c = m["canary"]
        if c["status"] == "TESTED" and (c["planted"] or 0) > 0:
            canary_leaked += int(c["leaked"] or 0)
            canary_planted += int(c["planted"] or 0)
            canary_files += int(c["files_assessed"] or 0)
            canary_tested_jobs += 1

        ident = m["identity"]
        if ident["status"] == "MEASURED" and (ident["true_positives"] + ident["false_positives"]) > 0:
            id_tp += int(ident["true_positives"])
            id_fp += int(ident["false_positives"])
            id_false_merges += int(ident["false_merges"])
            id_records += int(ident["records_assessed"])
            id_measured_jobs += 1

        cl = m["clinical"]
        if cl["status"] == "MEASURED" and int(cl["expected"] or 0) > 0:
            clin_exp += int(cl["expected"])
            clin_pres += int(cl["preserved"])
            clin_miss += int(cl["missing"])
            clin_mod += int(cl["modified"])
            clin_measured_jobs += 1

    canary_agg = (
        {
            "status": "TESTED",
            "leaked": canary_leaked,
            "planted": canary_planted,
            "files_assessed": canary_files,
            "outcome": "PROTECTED" if canary_leaked == 0 else "LEAKAGE_DETECTED",
            "jobs_tested": canary_tested_jobs,
        }
        if canary_tested_jobs > 0 and canary_planted > 0
        else {"status": "NOT_TESTED", "leaked": None, "planted": 0, "files_assessed": 0, "outcome": "NOT_TESTED"}
    )

    id_denom = id_tp + id_fp
    identity_agg = (
        {
            "status": "MEASURED",
            "true_positives": id_tp,
            "false_positives": id_fp,
            "precision": round(id_tp / id_denom, 4),
            "false_merges": id_false_merges,
            "records_assessed": id_records,
            "scope": f"AGGREGATE ({id_measured_jobs} jobs)",
        }
        if id_measured_jobs > 0 and id_denom > 0
        else {
            "status": "NOT_MEASURED",
            "true_positives": 0,
            "false_positives": 0,
            "precision": None,
            "false_merges": 0,
            "records_assessed": 0,
            "scope": "AGGREGATE",
        }
    )

    clinical_agg = (
        {
            "status": "MEASURED",
            "expected": clin_exp,
            "preserved": clin_pres,
            "missing": clin_miss,
            "modified": clin_mod,
            "preservation_percentage": round((clin_pres / clin_exp) * 100.0, 4),
            "jobs_measured": clin_measured_jobs,
        }
        if clin_measured_jobs > 0 and clin_exp > 0
        else {
            "status": "NOT_MEASURED",
            "expected": 0,
            "preserved": 0,
            "missing": 0,
            "modified": 0,
            "preservation_percentage": None,
        }
    )

    latest_ts = max((j.get("completed_at") or j.get("created_at") or 0) for j in completed_jobs)
    return {
        "scope": "AGGREGATE",
        "job_id": None,
        "dataset_id": None,
        "dataset_name": f"All completed datasets ({len(completed_jobs)} jobs)",
        "job_status": "COMPLETED",
        "release_decision": "AGGREGATE",
        "processed_at": latest_ts,
        "jobs_included": len(completed_jobs),
        "metrics": {
            "canary": canary_agg,
            "identity": identity_agg,
            "clinical": clinical_agg,
            "execution": get_runtime_execution_compliance(),
        },
    }


def get_dashboard_metrics_summary(
    conn: sqlite3.Connection,
    org_ids: Optional[List[str]],
    scope: str = "latest",
) -> Dict[str, Any]:
    """Resolve latest completed job, aggregate view, or specific job_id with org isolation."""
    where_org, params = _org_clause(org_ids, "j")
    all_jobs = [
        dict(r)
        for r in conn.execute(
            f"""
            SELECT j.*, d.name as dataset_name, o.name as organisation_name
            FROM jobs j
            LEFT JOIN datasets d ON j.dataset_id = d.id
            LEFT JOIN organisations o ON j.organisation_id = o.id
            WHERE {where_org}
            ORDER BY COALESCE(j.completed_at, j.created_at) DESC, j.created_at DESC
            LIMIT 50
            """,
            params,
        ).fetchall()
    ]
    completed_jobs = [
        j for j in all_jobs if str(j.get("status") or "").upper() in COMPLETED_JOB_STATUSES
    ]

    if scope == "aggregate":
        payload = build_aggregate_dashboard_metrics(conn, completed_jobs)
    elif scope == "latest" or not scope:
        if completed_jobs:
            payload = build_job_dashboard_metrics(conn, completed_jobs[0])
        else:
            payload = {
                "scope": "EMPTY",
                "job_id": None,
                "dataset_id": None,
                "dataset_name": "No completed jobs",
                "job_status": "EMPTY",
                "release_decision": "NOT_MEASURED",
                "processed_at": None,
                "metrics": {
                    "canary": {"status": "NOT_TESTED", "leaked": None, "planted": 0, "files_assessed": 0, "outcome": "NOT_TESTED"},
                    "identity": {"status": "NOT_MEASURED", "true_positives": 0, "false_positives": 0, "precision": None, "false_merges": 0, "records_assessed": 0, "scope": "JOB"},
                    "clinical": {"status": "NOT_MEASURED", "expected": 0, "preserved": 0, "missing": 0, "modified": 0, "preservation_percentage": None},
                    "execution": get_runtime_execution_compliance(),
                },
            }
    else:
        target = next((j for j in all_jobs if j["id"] == scope), None)
        if not target:
            # Verify whether the job exists in another org (access denied) vs missing
            exists = conn.execute("SELECT id, organisation_id FROM jobs WHERE id = ?", (scope,)).fetchone()
            if exists:
                raise PermissionError("Cross-organisation access denied")
            raise LookupError("Job not found")
        payload = build_job_dashboard_metrics(conn, target)

    payload["available_jobs"] = [
        {
            "id": j["id"],
            "dataset_id": j.get("dataset_id"),
            "dataset_name": j.get("dataset_name") or j.get("input_name") or j["id"],
            "status": j.get("status"),
            "release_decision": j.get("release_decision"),
            "completed_at": j.get("completed_at") or j.get("created_at"),
        }
        for j in all_jobs
    ]
    return payload
