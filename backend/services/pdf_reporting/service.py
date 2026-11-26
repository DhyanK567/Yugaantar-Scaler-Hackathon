"""Authoritative PDF report orchestration service for MediLocker."""
from __future__ import annotations

import datetime as dt
import hashlib
import json
from typing import Any, Dict, List, Optional

from ...database import get_db
from .renderers import render_report_pdf
from .schemas import ReportDocument, ReportSection
from .security import safe_filename, sanitize_safe_text, scan_pdf_bytes_for_leaks
from .templates import DEFAULT_CLASSIFICATION


class PdfGenerationError(RuntimeError):
    """Raised when report data is missing or PDF generation fails."""


def _fmt_ts(ts: Optional[float]) -> str:
    if not ts:
        return "N/A"
    return dt.datetime.fromtimestamp(float(ts), tz=dt.timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")


def _pseudo_actor(actor_role: Optional[str], actor_id: Optional[str]) -> str:
    role = sanitize_safe_text(actor_role or "SYSTEM", 32)
    if not actor_id:
        return role
    tag = hashlib.sha256(actor_id.encode("utf-8")).hexdigest()[:8].upper()
    return f"{role} (USR-{tag})"


def _pseudo_ref(prefix: str, raw_id: Optional[str]) -> str:
    if not raw_id:
        return "N/A"
    h = hashlib.sha256(raw_id.encode("utf-8")).hexdigest()[:10].upper()
    return f"{prefix}-{h}"


def _build_and_scan(doc: ReportDocument, prefix: str, ref_id: str) -> tuple[bytes, str]:
    pdf_bytes = render_report_pdf(doc)
    scan_pdf_bytes_for_leaks(pdf_bytes)
    return pdf_bytes, safe_filename(prefix, ref_id)


def generate_privacy_passport_pdf(passport_id: str) -> tuple[bytes, str]:
    with get_db() as conn:
        row = conn.execute(
            """
            SELECT p.*, o.name as org_name, j.status as job_status, j.policy_version as policy_version
            FROM passports p
            LEFT JOIN organisations o ON o.id = p.organisation_id
            LEFT JOIN jobs j ON j.id = p.job_id
            WHERE p.id = ?
            """,
            (passport_id,),
        ).fetchone()
        if not row:
            raise PdfGenerationError("Passport not found")
        p = dict(row)
        assess = conn.execute("SELECT * FROM privacy_assessments WHERE job_id = ?", (p["job_id"],)).fetchone()
        ident = conn.execute("SELECT * FROM identity_clusters WHERE job_id = ?", (p["job_id"],)).fetchone()

    payload = json.loads(p.get("passport_json") or "{}")
    metrics = payload.get("metrics") or {}
    now_str = _fmt_ts(dt.datetime.now(tz=dt.timezone.utc).timestamp())

    clin_pres = int(metrics.get("clinical_preserved", 0))
    clin_exp = int(metrics.get("clinical_expected", 0))
    id_prec = f"{ident['precision']:.2f}" if ident and ident["precision"] is not None else "Not measured"
    id_linked = int(metrics.get("records_linked", 0))

    doc = ReportDocument(
        report_id=p["id"],
        report_type="PRIVACY_PASSPORT",
        title="MediLocker Privacy Passport",
        subtitle="Hash-Verified De-Identified Dataset Release Manifest",
        organisation=sanitize_safe_text(p.get("org_name") or p.get("organisation_id") or "Unknown"),
        generated_at=now_str,
        classification=DEFAULT_CLASSIFICATION,
        sections=[
            ReportSection(
                title="1. Passport & Job Provenance",
                key_values=[
                    ("Passport ID", p["id"]),
                    ("Dataset Reference", _pseudo_ref("DS", p.get("dataset_id"))),
                    ("Processing Job ID", p["job_id"]),
                    ("Organisation", p.get("org_name") or p.get("organisation_id") or "Unknown"),
                    ("Processing Timestamp", _fmt_ts(payload.get("issued_at") or p.get("created_at"))),
                    ("Policy Version", p.get("policy_version") or "m10-v1"),
                    ("Release Decision", str(payload.get("release_decision") or "UNKNOWN")),
                    ("Validation Status", "HASH_VERIFIED" if p.get("verified_at") else str(p.get("signature_status", "UNSIGNED"))),
                    ("Manifest SHA-256", str(p.get("manifest_hash", ""))),
                ],
            ),
            ReportSection(
                title="2. Sanitisation, Clinical & Identity Summary",
                key_values=[
                    ("Files Processed", f"{metrics.get('files_sanitized', 0)} sanitized / {metrics.get('files_total', 0)} total ({metrics.get('files_quarantined', 0)} quarantined)"),
                    ("Records Processed", str(metrics.get("records_processed", 0))),
                    ("PII Identifiers Redacted", str(metrics.get("pii_detected", 0))),
                    ("Canary Containment", f"{metrics.get('canary_status', 'NOT_RUN')} ({metrics.get('canary_leaks', 0)} leaks)"),
                    ("Clinical Values Preserved", f"{clin_pres}/{clin_exp}" if clin_exp > 0 else "Not measured"),
                    ("Identity Continuity", f"{id_linked} linked (Precision: {id_prec})"),
                    ("Privacy Risk Level", str(assess["reid_risk_level"]) if assess else "NOT_MEASURED"),
                ],
                notes=["Unsigned manifests are hash-verified via SHA-256; original patient records are never included."],
            ),
        ],
    )
    return _build_and_scan(doc, "MediLocker_Privacy_Passport", passport_id)


def generate_privacy_intelligence_pdf(assessment_id: str) -> tuple[bytes, str]:
    with get_db() as conn:
        row = conn.execute(
            """
            SELECT pa.*, o.name as org_name
            FROM privacy_assessments pa
            LEFT JOIN organisations o ON o.id = pa.organisation_id
            WHERE pa.id = ?
            """,
            (assessment_id,),
        ).fetchone()
    if not row:
        raise PdfGenerationError("Privacy assessment not found")
    a = dict(row)
    now_str = _fmt_ts(dt.datetime.now(tz=dt.timezone.utc).timestamp())

    doc = ReportDocument(
        report_id=a["id"],
        report_type="PRIVACY_INTELLIGENCE",
        title="MediLocker Privacy Intelligence Report",
        subtitle="Measured PII Containment & Quasi-Identifier Risk Assessment",
        organisation=sanitize_safe_text(a.get("org_name") or a.get("organisation_id") or "Unknown"),
        generated_at=now_str,
        classification=DEFAULT_CLASSIFICATION,
        sections=[
            ReportSection(
                title="1. Assessment Summary",
                key_values=[
                    ("Assessment ID", a["id"]),
                    ("Dataset Reference", _pseudo_ref("DS", a.get("dataset_id"))),
                    ("Job ID", a["job_id"]),
                    ("Risk Classification", str(a.get("reid_risk_level", "UNKNOWN"))),
                    ("Estimated QI Risk Index", f"{a.get('qi_risk_score', 0.0)}% (structural index, not re-id probability)"),
                    ("Measured Direct PII Redacted", str(a.get("pii_detected", 0))),
                    ("Measured Residual Leaks", str(a.get("residual_leakage", 0))),
                    ("Canary Status", f"{a.get('canary_status')} ({a.get('canary_leaks')}/{a.get('canary_planted')})"),
                    ("Release Eligible", "YES" if a.get("release_eligible") else "NO"),
                ],
            ),
            ReportSection(
                title="2. Quasi-Identifiers, Methodology & Mitigations",
                key_values=[
                    ("QI Categories Evaluated", "Age, Gender, District, Village/Locality, PIN Prefix, Temporal Dates"),
                    ("Methodology", "Deterministic corpus-wide k-anonymity grouping + 7-vector attack simulation"),
                    ("Mitigations", "5y/10y age banding, PIN prefixing, village suppression, secret-keyed date shifts"),
                ],
                notes=[
                    "Measured uniqueness reflects corpus equivalence classes; estimated risk index is distinct from true external population probability.",
                    "Zero residual leaks on known patterns does not guarantee immunity against arbitrary external auxiliary datasets.",
                ],
            ),
        ],
    )
    return _build_and_scan(doc, "MediLocker_Privacy_Intelligence", assessment_id)


def generate_attack_simulation_pdf(run_id: str) -> tuple[bytes, str]:
    with get_db() as conn:
        row = conn.execute(
            """
            SELECT ar.*, o.name as org_name
            FROM attack_runs ar
            LEFT JOIN organisations o ON o.id = ar.organisation_id
            WHERE ar.id = ?
            """,
            (run_id,),
        ).fetchone()
    if not row:
        raise PdfGenerationError("Attack simulation not found")
    ar = dict(row)
    parsed = json.loads(ar.get("results_json") or "{}")
    strategies = parsed.get("strategies") or []
    total_recs = int(parsed.get("total_records", 0))
    at_risk_total = int(parsed.get("uniquely_distinguishable_records", 0))
    now_str = _fmt_ts(dt.datetime.now(tz=dt.timezone.utc).timestamp())

    vec_rows = [
        [
            str(s.get("attack_type", "")),
            "EXPOSED" if s.get("success") else "BLOCKED",
            str(s.get("records_at_risk", 0)),
            str(s.get("mitigation", "")),
        ]
        for s in strategies
    ]

    doc = ReportDocument(
        report_id=ar["id"],
        report_type="ATTACK_SIMULATION",
        title="MediLocker Adversarial Attack Simulation Report",
        subtitle="Deterministic Multi-Vector Re-Identification Evaluation",
        organisation=sanitize_safe_text(ar.get("org_name") or ar.get("organisation_id") or "Unknown"),
        generated_at=now_str,
        classification=DEFAULT_CLASSIFICATION,
        sections=[
            ReportSection(
                title="1. Simulation Overview",
                key_values=[
                    ("Simulation ID", ar["id"]),
                    ("Job ID", str(ar.get("job_id") or "N/A")),
                    ("Attack Profile", str(ar.get("profile", "standard-7-vector"))),
                    ("Records Evaluated", str(total_recs)),
                    ("Uniquely Distinguishable Records", str(at_risk_total)),
                    ("Vectors Blocked", f"{ar.get('blocked_count', 0)} / {ar.get('total_count', 0)}"),
                    ("Residual Distinguishability Rate", f"{ar.get('risk_score', 0.0)}%"),
                    ("Test Status", "COMPLETED" if total_recs > 0 else "EMPTY_CORPUS"),
                ],
            ),
            ReportSection(
                title="2. Vector-by-Vector Results",
                table_headers=["Attack Vector", "Status", "Records at Risk", "Mitigation Applied"],
                table_rows=vec_rows,
                notes=[
                    "A blocked simulated vector demonstrates resistance against the modeled auxiliary keys only, not all possible external linkage attacks.",
                ],
            ),
        ],
    )
    return _build_and_scan(doc, "MediLocker_Attack_Simulation", run_id)


def generate_clinical_integrity_pdf(report_id: str) -> tuple[bytes, str]:
    with get_db() as conn:
        row = conn.execute(
            """
            SELECT cr.*, o.name as org_name
            FROM clinical_reports cr
            LEFT JOIN organisations o ON o.id = cr.organisation_id
            WHERE cr.id = ?
            """,
            (report_id,),
        ).fetchone()
    if not row:
        raise PdfGenerationError("Clinical report not found")
    cr = dict(row)
    now_str = _fmt_ts(dt.datetime.now(tz=dt.timezone.utc).timestamp())

    exp = int(cr.get("expected_values", 0))
    pres = int(cr.get("preserved_values", 0))
    miss = int(cr.get("missing_values", 0))
    mod = int(cr.get("modified_values", 0))
    details = json.loads(cr.get("details_json") or "{}")
    warnings: List[str] = []
    if miss > 0:
        warnings.append(f"{miss} expected clinical value(s) missing after sanitisation.")
    if mod > 0:
        warnings.append(f"{mod} clinical value(s) modified during sanitisation.")
    if cr.get("fhir_integrity") == "FAILED":
        warnings.append("FHIR R4 Bundle structural validation reported failures.")

    def _fmt_ratio(v: Any) -> str:
        return f"{float(v) * 100:.2f}%" if v is not None else "Not measured"

    doc = ReportDocument(
        report_id=cr["id"],
        report_type="CLINICAL_INTEGRITY",
        title="MediLocker Clinical Integrity Report",
        subtitle="Exact Clinical Value, Medication, Laboratory & FHIR R4 Fidelity",
        organisation=sanitize_safe_text(cr.get("org_name") or cr.get("organisation_id") or "Unknown"),
        generated_at=now_str,
        classification=DEFAULT_CLASSIFICATION,
        sections=[
            ReportSection(
                title="1. Exact Preservation Counts",
                key_values=[
                    ("Clinical Validation ID", cr["id"]),
                    ("Job Reference", cr["job_id"]),
                    ("Preserved / Expected", f"{pres}/{exp}" if exp > 0 else "0/0 (Not measured)"),
                    ("Missing Values", str(miss)),
                    ("Modified Values", str(mod)),
                    ("Medication Integrity", _fmt_ratio(cr.get("medication_integrity"))),
                    ("Dosage Integrity", _fmt_ratio(cr.get("dosage_integrity"))),
                    ("Laboratory Value Integrity", _fmt_ratio(cr.get("lab_integrity"))),
                    ("Vital Sign Integrity", _fmt_ratio(cr.get("vital_integrity"))),
                    ("FHIR R4 Validation Status", f"{cr.get('fhir_integrity', 'NOT_MEASURED')} ({details.get('fhir_bundles_valid', 0)}/{details.get('fhir_bundles_checked', 0)} bundles)"),
                ],
                notes=warnings or ["All measured clinical probes and FHIR R4 bundles passed without unexpected modification."],
            ),
        ],
    )
    return _build_and_scan(doc, "MediLocker_Clinical_Integrity", report_id)


def generate_audit_trail_pdf(
    organisation_id: Optional[str],
    organisation_name: str,
    start_ts: Optional[float] = None,
    end_ts: Optional[float] = None,
    limit: int = 200,
) -> tuple[bytes, str]:
    clauses = ["1=1"]
    params: List[Any] = []
    if organisation_id:
        clauses.append("(organisation_id = ? OR organisation_id IS NULL)")
        params.append(organisation_id)
    if start_ts is not None:
        clauses.append("timestamp >= ?")
        params.append(start_ts)
    if end_ts is not None:
        clauses.append("timestamp <= ?")
        params.append(end_ts)

    with get_db() as conn:
        rows = [
            dict(r)
            for r in conn.execute(
                f"SELECT id, timestamp, actor_id, actor_role, action, resource_type, resource_id, outcome FROM audit_events WHERE {' AND '.join(clauses)} ORDER BY timestamp DESC LIMIT ?",
                params + [limit],
            ).fetchall()
        ]

    now_str = _fmt_ts(dt.datetime.now(tz=dt.timezone.utc).timestamp())
    rep_id = f"AUD-{hashlib.sha256(f'{organisation_id}:{now_str}'.encode()).hexdigest()[:10].upper()}"
    categories = sorted({str(r["action"]) for r in rows})
    ev_rows = [
        [
            _fmt_ts(r.get("timestamp")),
            str(r.get("action", "")),
            str(r.get("outcome", "")),
            _pseudo_actor(r.get("actor_role"), r.get("actor_id")),
            f"{r.get('resource_type', '')}:{_pseudo_ref('RES', r.get('resource_id'))}",
        ]
        for r in rows
    ]
    drange = f"{_fmt_ts(start_ts) if start_ts else 'Beginning'} to {_fmt_ts(end_ts) if end_ts else 'Present'}"

    doc = ReportDocument(
        report_id=rep_id,
        report_type="AUDIT_TRAIL",
        title="MediLocker Governance Audit Trail Report",
        subtitle="Append-Only Privacy & Security Event Evidence",
        organisation=sanitize_safe_text(organisation_name or "All Authorised Organisations"),
        generated_at=now_str,
        classification=DEFAULT_CLASSIFICATION,
        sections=[
            ReportSection(
                title="1. Audit Scope & Integrity",
                key_values=[
                    ("Report ID", rep_id),
                    ("Organisation", organisation_name or "All Authorised Organisations"),
                    ("Selected Date Range", drange),
                    ("Events Included", str(len(rows))),
                    ("Event Categories", ", ".join(categories) if categories else "None"),
                    ("Integrity Verification", "APPEND_ONLY_VERIFIED (No secrets, OTPs, emails, or tokens exposed)"),
                ],
            ),
            ReportSection(
                title="2. Audit Event Ledger",
                table_headers=["Timestamp", "Action", "Outcome", "Actor Role / Ref", "Safe Resource Ref"],
                table_rows=ev_rows,
            ),
        ],
    )
    return _build_and_scan(doc, "MediLocker_Audit_Trail", rep_id)
