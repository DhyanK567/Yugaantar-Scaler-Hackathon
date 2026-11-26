"""M10.2 — Deterministic Synthetic Re-identification Attack Simulator.

Evaluates 7 combination-based re-identification attack strategies against
corpus record profiles (before and after mitigation) without ever emitting
raw PII or patient names in reports.
"""
from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field


@dataclass(frozen=True)
class RecordProfile:
    """De-identified structural profile of a record for risk/attack evaluation.
    Values are structural buckets or hashed/normalized tokens—never exported raw in reports.
    """
    record_id: str
    patient_key: str  # cluster key or record_id if unlinked
    age_val: str = ""  # exact age (pre) or age band (post)
    birth_year: str = ""
    gender: str = ""
    district: str = ""
    village_or_loc: str = ""
    pin: str = ""
    hospital_dept: str = ""
    admission_date: str = ""
    los_days: str = ""
    diagnosis: str = ""
    treatment: str = ""
    hospital_count: int = 1
    record_count: int = 1


@dataclass
class AttackFinding:
    strategy: str
    record_id: str
    candidate_group_size: int
    unique_candidate_patients: int
    uniquely_distinguishable: bool
    risk_category: str
    responsible_fields: list[str]
    attack_succeeded: bool
    recommended_mitigation: str


@dataclass
class AttackSimulationSummary:
    total_records: int
    strategies_run: list[str]
    strategy_success_counts: dict[str, int]
    uniquely_distinguishable_records: int
    findings: list[AttackFinding] = field(default_factory=list)


def _risk_cat_for_group(k: int, min_group: int) -> str:
    if k <= 1:
        return "CRITICAL"
    if k < max(2, min_group // 2 + 1):
        return "HIGH"
    if k < min_group:
        return "MODERATE"
    return "LOW"


def _mitigation_for(strategy: str, fields: list[str]) -> str:
    if "village_or_loc" in fields:
        return "SUPPRESS_VILLAGE_AND_LOCALITY"
    if "pin" in fields:
        return "GENERALIZE_OR_SUPPRESS_PIN"
    if "admission_date" in fields or "los_days" in fields:
        return "SHIFT_DATES_AND_BAND_LOS"
    if "age" in fields:
        return "WIDEN_AGE_BAND_10Y"
    if "hospital_dept" in fields:
        return "GENERALIZE_DEPARTMENT_OR_BAND_AGE"
    if strategy == "cross_record_linkage":
        return "ROTATE_PSEUDONYM_AND_MINIMIZE_QI"
    return "SELECTIVE_QI_SUPPRESSION"


def simulate_attacks(
    profiles: list[RecordProfile],
    min_group_size: int = 5,
    include_low_findings: bool = False,
) -> AttackSimulationSummary:
    """Run all 7 deterministic re-identification attack strategies on profiles."""
    strategies: list[tuple[str, list[str], callable]] = [
        (
            "exact_combination",
            ["age", "birth_year", "gender", "district", "village_or_loc", "pin"],
            lambda p: (p.age_val, p.birth_year, p.gender, p.district, p.village_or_loc, p.pin),
        ),
        (
            "age_gender_location",
            ["age", "gender", "district", "pin"],
            lambda p: (p.age_val, p.gender, p.district, p.pin),
        ),
        (
            "rare_diagnosis_location",
            ["diagnosis", "district", "village_or_loc"],
            lambda p: (p.diagnosis, p.district, p.village_or_loc),
        ),
        (
            "admission_los",
            ["admission_date", "los_days"],
            lambda p: (p.admission_date, p.los_days),
        ),
        (
            "geographic_narrowing",
            ["district", "village_or_loc", "pin"],
            lambda p: (p.district, p.village_or_loc, p.pin),
        ),
        (
            "cross_record_linkage",
            ["hospital_count", "record_count", "gender", "district"],
            lambda p: (
                str(p.hospital_count) if p.hospital_count > 1 else "",
                str(p.record_count) if p.record_count > 2 else "",
                p.gender,
                p.district,
            ),
        ),
        (
            "rare_attribute_combination",
            ["age", "gender", "hospital_dept", "treatment"],
            lambda p: (p.age_val, p.gender, p.hospital_dept, p.treatment),
        ),
    ]

    success_counts: dict[str, int] = {name: 0 for name, _, _ in strategies}
    distinguishable_rids: set[str] = set()
    findings: list[AttackFinding] = []

    for strat_name, fields, key_fn in strategies:
        groups: dict[tuple[str, ...], list[RecordProfile]] = defaultdict(list)
        for prof in profiles:
            key = key_fn(prof)
            # Skip attack if fewer than 2 non-empty QI dimensions are present
            non_empty = [f for f, v in zip(fields, key) if v]
            if len(non_empty) < 2:
                continue
            groups[key].append(prof)

        for key, members in groups.items():
            k = len(members)
            unique_pts = len({m.patient_key for m in members})
            active_fields = [f for f, v in zip(fields, key) if v]
            is_unique = k == 1 or unique_pts == 1
            succeeded = is_unique and len(active_fields) >= 2
            cat = _risk_cat_for_group(unique_pts, min_group_size)
            if succeeded:
                success_counts[strat_name] += len(members)
                for m in members:
                    distinguishable_rids.add(m.record_id)
            if succeeded or cat in ("HIGH", "CRITICAL") or include_low_findings:
                for m in members:
                    findings.append(
                        AttackFinding(
                            strategy=strat_name,
                            record_id=m.record_id,
                            candidate_group_size=k,
                            unique_candidate_patients=unique_pts,
                            uniquely_distinguishable=is_unique,
                            risk_category=cat,
                            responsible_fields=active_fields,
                            attack_succeeded=succeeded,
                            recommended_mitigation=_mitigation_for(strat_name, active_fields),
                        )
                    )

    return AttackSimulationSummary(
        total_records=len(profiles),
        strategies_run=[s[0] for s in strategies],
        strategy_success_counts=success_counts,
        uniquely_distinguishable_records=len(distinguishable_rids),
        findings=findings,
    )
