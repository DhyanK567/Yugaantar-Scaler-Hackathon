"""M10.5 — Adaptive Generalisation & Suppression Mitigation Engine.

Selects the least-destructive deterministic privacy transformation per record
based on its combination-based risk assessment, while strictly preserving
clinical diagnoses, vitals, medications, dosages, and temporal intervals.
Never stores raw PII in mitigation records.
"""
from __future__ import annotations

from dataclasses import dataclass, field

from .risk_engine import RecordRiskAssessment


@dataclass(frozen=True)
class MitigationRecord:
    record_id: str
    field_category: str
    action: str
    reason_code: str
    policy_version: str


@dataclass
class MitigationPlan:
    age_band_width: int = 5
    suppress_pin: bool = False
    suppress_district: bool = False
    suppress_tehsil: bool = False
    suppress_village: bool = True
    shift_dates: bool = True
    records: list[MitigationRecord] = field(default_factory=list)


def plan_record_mitigation(
    assessment: RecordRiskAssessment,
    policy: dict,
    has_age: bool = False,
    has_date: bool = False,
    has_pin: bool = False,
    has_district: bool = False,
    has_village: bool = False,
) -> MitigationPlan:
    """Compute adaptive, least-destructive mitigation actions for a record."""
    policy_ver = str(policy.get("policy_version", "m10-v1"))
    default_width = int(policy.get("age_band_years", 5))
    cat = assessment.risk_category
    plan = MitigationPlan(age_band_width=default_width)

    # Always apply baseline deterministic protections for direct/quasi fields
    if has_village:
        plan.suppress_village = True
        plan.records.append(MitigationRecord(
            assessment.record_id, "B_QUASI_IDENTIFIER", "SUPPRESS_VILLAGE",
            "BASE_VILLAGE_PROTECTION", policy_ver,
        ))
    if has_date:
        plan.shift_dates = True
        plan.records.append(MitigationRecord(
            assessment.record_id, "B_QUASI_IDENTIFIER", "SHIFT_DATE_SECRET_OFFSET",
            "BASE_TEMPORAL_SHIFT", policy_ver,
        ))

    # Adaptive escalation only when justified by combination risk
    if cat in ("HIGH", "CRITICAL") or assessment.below_min_group:
        if has_age:
            plan.age_band_width = 10
            plan.records.append(MitigationRecord(
                assessment.record_id, "B_QUASI_IDENTIFIER", "WIDEN_AGE_BAND_10Y",
                "RARE_GROUP_AGE_GENERALIZATION", policy_ver,
            ))
        if has_pin:
            if cat == "CRITICAL":
                plan.suppress_pin = True
                plan.records.append(MitigationRecord(
                    assessment.record_id, "B_QUASI_IDENTIFIER", "SUPPRESS_PIN_FULL",
                    "CRITICAL_GEO_SUPPRESSION", policy_ver,
                ))
            else:
                plan.records.append(MitigationRecord(
                    assessment.record_id, "B_QUASI_IDENTIFIER", "MASK_PIN_PREFIX",
                    "MODERATE_GEO_GENERALIZATION", policy_ver,
                ))
        if cat == "CRITICAL" and has_district:
            plan.suppress_district = True
            plan.suppress_tehsil = True
            plan.records.append(MitigationRecord(
                assessment.record_id, "B_QUASI_IDENTIFIER", "SUPPRESS_DISTRICT_TEHSIL",
                "CRITICAL_COMBO_GEO_SUPPRESSION", policy_ver,
            ))
    else:
        if has_age:
            plan.records.append(MitigationRecord(
                assessment.record_id, "B_QUASI_IDENTIFIER", f"AGE_BAND_{default_width}Y",
                "BASE_AGE_GENERALIZATION", policy_ver,
            ))
        if has_pin:
            plan.records.append(MitigationRecord(
                assessment.record_id, "B_QUASI_IDENTIFIER", "MASK_PIN_PREFIX",
                "BASE_PIN_PREFIX", policy_ver,
            ))

    return plan
