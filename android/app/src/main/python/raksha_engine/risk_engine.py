"""M10.3 & M10.4 — Combination-Based Risk Engine & Rare Group/Attribute Protection.

Evaluates multi-attribute quasi-identifier combinations rather than isolated fields.
Clearly separates *measured uniqueness* (group size k, corpus uniqueness) from
*estimated structural risk index* (0-100 configurable weighted score).
"""
from __future__ import annotations

from collections import Counter
from dataclasses import dataclass, field

from .attacker import RecordProfile


@dataclass(frozen=True)
class RiskWeights:
    group_size: int = 35
    qi_uniqueness: int = 25
    geo_rarity: int = 15
    temporal: int = 10
    rare_dx: int = 10
    linkage: int = 5


@dataclass
class RecordRiskAssessment:
    record_id: str
    measured_group_size: int
    measured_is_unique: bool
    estimated_risk_score: int  # 0..100 structural index (not a re-id probability)
    risk_category: str  # LOW | MODERATE | HIGH | CRITICAL
    below_min_group: bool
    contributing_factors: list[str] = field(default_factory=list)
    recommended_mitigations: list[str] = field(default_factory=list)


@dataclass
class CorpusRiskSummary:
    total_records: int
    unique_candidate_groups: int
    records_below_min_group: int
    category_counts: dict[str, int]
    assessments: dict[str, RecordRiskAssessment]


def _category_from_score(score: int, policy: dict) -> str:
    if score >= int(policy.get("risk_threshold_critical", 75)):
        return "CRITICAL"
    if score >= int(policy.get("risk_threshold_high", 50)):
        return "HIGH"
    if score >= int(policy.get("risk_threshold_moderate", 25)):
        return "MODERATE"
    return "LOW"


def evaluate_corpus_risk(
    profiles: list[RecordProfile],
    policy: dict,
) -> CorpusRiskSummary:
    """Compute combination-based risk assessments across all corpus record profiles."""
    min_group = int(policy.get("min_group_size", 5))
    weights = RiskWeights(
        group_size=int(policy.get("weight_group_size", 35)),
        qi_uniqueness=int(policy.get("weight_qi_uniqueness", 25)),
        geo_rarity=int(policy.get("weight_geo_rarity", 15)),
        temporal=int(policy.get("weight_temporal", 10)),
        rare_dx=int(policy.get("weight_rare_dx", 10)),
        linkage=int(policy.get("weight_linkage", 5)),
    )

    qi_counts: Counter[tuple[str, ...]] = Counter()
    geo_counts: Counter[tuple[str, str, str]] = Counter()
    temp_counts: Counter[tuple[str, str]] = Counter()
    dx_counts: Counter[str] = Counter()
    dept_counts: Counter[str] = Counter()

    for p in profiles:
        qi_key = (p.age_val, p.gender, p.district, p.pin, p.village_or_loc)
        qi_counts[qi_key] += 1
        if p.district or p.pin or p.village_or_loc:
            geo_counts[(p.district, p.village_or_loc, p.pin)] += 1
        if p.admission_date or p.los_days:
            temp_counts[(p.admission_date, p.los_days)] += 1
        if p.diagnosis:
            dx_counts[p.diagnosis] += 1
        if p.hospital_dept:
            dept_counts[p.hospital_dept] += 1

    assessments: dict[str, RecordRiskAssessment] = {}
    cat_counts: dict[str, int] = {"LOW": 0, "MODERATE": 0, "HIGH": 0, "CRITICAL": 0}
    below_min = 0

    for p in profiles:
        qi_key = (p.age_val, p.gender, p.district, p.pin, p.village_or_loc)
        k = qi_counts[qi_key]
        is_unique = k == 1 and any(qi_key)
        is_rare_group = k < min_group and any(qi_key)
        if is_rare_group:
            below_min += 1

        score = 0
        factors: list[str] = []
        mitigations: list[str] = []

        # 1. Candidate group size
        if any(qi_key):
            if k == 1:
                score += weights.group_size
                factors.append("UNIQUE_QI_GROUP_K1")
            elif k < min_group:
                ratio = (min_group - k) / max(1, min_group)
                score += int(round(weights.group_size * max(0.4, ratio)))
                factors.append("SMALL_QI_GROUP")

        # 2. Multi-attribute QI uniqueness
        active_qi = sum(1 for v in qi_key if v)
        if is_unique and active_qi >= 3:
            score += weights.qi_uniqueness
            factors.append("MULTI_QI_UNIQUE")
            mitigations.append("WIDEN_AGE_BAND_AND_GENERALIZE_QI")
        elif is_rare_group and active_qi >= 2:
            score += weights.qi_uniqueness // 2
            factors.append("MULTI_QI_NARROW")

        # 3. Geographic rarity
        geo_k = geo_counts.get((p.district, p.village_or_loc, p.pin), min_group)
        if (p.village_or_loc or p.pin) and geo_k < min_group:
            score += weights.geo_rarity
            factors.append("GEOGRAPHIC_RARITY")
            if p.village_or_loc:
                mitigations.append("SUPPRESS_VILLAGE_LOCALITY")
            if p.pin:
                mitigations.append("GENERALIZE_OR_SUPPRESS_PIN")

        # 4. Temporal uniqueness (admission date + LOS)
        if p.admission_date and temp_counts.get((p.admission_date, p.los_days), min_group) < min_group:
            score += weights.temporal
            factors.append("TEMPORAL_UNIQUENESS")
            mitigations.append("SHIFT_DATES_SECRET_OFFSET")

        # 5. Rare diagnosis / department combination (never remove diagnosis!)
        if p.diagnosis and dx_counts[p.diagnosis] < min_group and (p.village_or_loc or p.admission_date):
            score += weights.rare_dx
            factors.append("RARE_DX_WITH_QI")
            mitigations.append("PROTECT_QI_KEEP_DIAGNOSIS")
        elif p.hospital_dept and dept_counts[p.hospital_dept] < min_group:
            score += weights.rare_dx // 2
            factors.append("SMALL_DEPARTMENT")
            mitigations.append("GENERALIZE_AGE_BAND")

        # 6. Cross-record linkability
        if p.hospital_count > 1 or p.record_count > 2:
            score += weights.linkage
            factors.append("CROSS_RECORD_LINKABLE")

        score = min(100, score)
        cat = _category_from_score(score, policy)
        cat_counts[cat] += 1

        assessments[p.record_id] = RecordRiskAssessment(
            record_id=p.record_id,
            measured_group_size=k,
            measured_is_unique=is_unique,
            estimated_risk_score=score,
            risk_category=cat,
            below_min_group=is_rare_group,
            contributing_factors=factors,
            recommended_mitigations=sorted(set(mitigations)),
        )

    return CorpusRiskSummary(
        total_records=len(profiles),
        unique_candidate_groups=len(qi_counts),
        records_below_min_group=below_min,
        category_counts=cat_counts,
        assessments=assessments,
    )
