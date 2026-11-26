"""Strict allowlist schemas for MediLocker operational PDF reports."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Optional


@dataclass(frozen=True)
class ReportSection:
    title: str
    key_values: List[tuple[str, str]] = field(default_factory=list)
    table_headers: List[str] = field(default_factory=list)
    table_rows: List[List[str]] = field(default_factory=list)
    notes: List[str] = field(default_factory=list)


@dataclass(frozen=True)
class ReportDocument:
    report_id: str
    report_type: str
    title: str
    subtitle: str
    organisation: str
    generated_at: str
    classification: str
    sections: List[ReportSection]


@dataclass(frozen=True)
class PrivacyPassportReportData:
    passport_id: str
    dataset_ref: str
    job_id: str
    organisation: str
    processing_timestamp: str
    policy_version: str
    files_total: int
    files_sanitized: int
    files_quarantined: int
    records_processed: int
    pii_detected: int
    clinical_preserved: int
    clinical_expected: int
    identity_linked: int
    identity_precision: str
    privacy_risk_level: str
    release_decision: str
    manifest_hash: str
    signature_status: str
    validation_status: str


@dataclass(frozen=True)
class PrivacyIntelligenceReportData:
    assessment_id: str
    dataset_ref: str
    job_id: str
    organisation: str
    generated_at: str
    risk_level: str
    qi_risk_score: float
    pii_detected: int
    residual_leakage: int
    canary_status: str
    canary_leaks: int
    canary_planted: int
    qi_categories_evaluated: List[str]
    measured_uniqueness: str
    methodology: str
    mitigations: List[str]
    limitations: List[str]
    before_after_rows: List[List[str]] = field(default_factory=list)


@dataclass(frozen=True)
class AttackSimulationReportData:
    simulation_id: str
    job_id: str
    organisation: str
    generated_at: str
    profile: str
    records_evaluated: int
    records_at_risk: int
    vectors_blocked: int
    vectors_total: int
    residual_distinguishability_pct: float
    test_status: str
    vector_rows: List[List[str]]
    mitigations_applied: List[str]
    limitations: List[str]


@dataclass(frozen=True)
class ClinicalIntegrityReportData:
    clinical_report_id: str
    job_id: str
    organisation: str
    generated_at: str
    expected_values: int
    preserved_values: int
    missing_values: int
    modified_values: int
    medication_integrity: str
    dosage_integrity: str
    lab_integrity: str
    vital_integrity: str
    fhir_validation_status: str
    fhir_bundles_checked: int
    fhir_bundles_valid: int
    warnings: List[str]


@dataclass(frozen=True)
class AuditTrailReportData:
    report_id: str
    organisation: str
    date_range: str
    generated_at: str
    total_events: int
    categories: List[str]
    integrity_status: str
    event_rows: List[List[str]]
