"""M10.6 & M10.7 — Privacy-Utility Measurement & Release Gate.

Separately measures privacy metrics (attack surface, group sizes, direct
identifier counts) and clinical utility metrics (exact numerator/denominator
preservation without rounding 4853/4855 to 100%).
Produces deterministic PASS / PASS_WITH_WARNINGS / BLOCKED release decisions.
"""
from __future__ import annotations

from dataclasses import dataclass, field

from .attacker import AttackSimulationSummary
from .risk_engine import CorpusRiskSummary


@dataclass
class PrivacyMetrics:
    direct_identifiers_detected: int
    pre_attack_successes: int
    post_attack_successes: int
    pre_uniquely_distinguishable: int
    post_uniquely_distinguishable: int
    unique_candidate_groups: int
    records_below_min_group: int
    generalizations_applied: int
    suppressions_applied: int
    files_quarantined: int


@dataclass
class ClinicalUtilityMetrics:
    records_processed: int
    records_linked: int
    clinical_values_preserved: int | None = None
    clinical_values_total: int | None = None

    def preservation_ratio(self) -> float | None:
        if self.clinical_values_preserved is None or not self.clinical_values_total:
            return None
        return self.clinical_values_preserved / self.clinical_values_total

    def exact_fraction_str(self) -> str:
        if self.clinical_values_preserved is None or self.clinical_values_total is None:
            return "n/a"
        return f"{self.clinical_values_preserved}/{self.clinical_values_total}"


@dataclass
class ReleaseDecision:
    status: str  # PASS | PASS_WITH_WARNINGS | BLOCKED
    policy_version: str
    reason_codes: list[str] = field(default_factory=list)
    risk_categories: dict[str, int] = field(default_factory=dict)
    affected_record_counts: dict[str, int] = field(default_factory=dict)
    recommended_mitigation: list[str] = field(default_factory=list)
    safe_audit_metadata: dict[str, object] = field(default_factory=dict)


def evaluate_release_gate(
    privacy: PrivacyMetrics,
    utility: ClinicalUtilityMetrics,
    post_risk: CorpusRiskSummary,
    pre_attack: AttackSimulationSummary,
    post_attack: AttackSimulationSummary,
    policy: dict,
    direct_leaks_observed: int = 0,
) -> ReleaseDecision:
    """Evaluate release eligibility from configurable policy thresholds."""
    policy_ver = str(policy.get("policy_version", "m10-v1"))
    max_crit = int(policy.get("max_critical_records_for_pass", 0))
    max_high_ratio = float(policy.get("max_high_risk_ratio_for_pass", 0.15))
    min_clin_ratio = float(policy.get("min_clinical_retention_ratio", 0.90))

    total = max(1, post_risk.total_records)
    crit_count = post_risk.category_counts.get("CRITICAL", 0)
    high_count = post_risk.category_counts.get("HIGH", 0)
    mod_count = post_risk.category_counts.get("MODERATE", 0)
    high_ratio = high_count / total

    reasons: list[str] = []
    recs: list[str] = []
    blocked = False
    warned = False

    if direct_leaks_observed > 0:
        blocked = True
        reasons.append("DIRECT_PII_LEAK_DETECTED")
        recs.append("EXPAND_DIRECT_IDENTIFIER_REDACTION")

    if crit_count > max_crit:
        blocked = True
        reasons.append("CRITICAL_REIDENTIFICATION_RISK_EXCEEDED")
        recs.append("APPLY_ADAPTIVE_SUPPRESSION_TO_CRITICAL_RECORDS")

    clin_ratio = utility.preservation_ratio()
    if clin_ratio is not None and clin_ratio < min_clin_ratio:
        blocked = True
        reasons.append("CLINICAL_UTILITY_BELOW_THRESHOLD")
        recs.append("RELAX_OVER_BROAD_REDACTION_ON_CLINICAL_FIELDS")

    if high_ratio > max_high_ratio:
        warned = True
        reasons.append("HIGH_RISK_RECORD_RATIO_ELEVATED")
        recs.append("INCREASE_AGE_BAND_OR_GENERALIZE_LOCATION")

    if post_attack.uniquely_distinguishable_records > 0 and not blocked:
        warned = True
        reasons.append("RESIDUAL_UNIQUE_QUASI_COMBINATIONS")
        recs.append("REVIEW_RARE_QUASI_IDENTIFIER_COMBINATIONS")

    if not reasons:
        reasons.append("ALL_POLICY_GATES_SATISFIED")

    status = "BLOCKED" if blocked else ("PASS_WITH_WARNINGS" if warned else "PASS")
    return ReleaseDecision(
        status=status,
        policy_version=policy_ver,
        reason_codes=reasons,
        risk_categories=dict(post_risk.category_counts),
        affected_record_counts={
            "critical": crit_count,
            "high": high_count,
            "moderate": mod_count,
            "below_min_group": post_risk.records_below_min_group,
            "post_uniquely_distinguishable": post_attack.uniquely_distinguishable_records,
        },
        recommended_mitigation=sorted(set(recs)),
        safe_audit_metadata={
            "pre_attack_uniquely_distinguishable": pre_attack.uniquely_distinguishable_records,
            "post_attack_uniquely_distinguishable": post_attack.uniquely_distinguishable_records,
            "pre_attack_successes": pre_attack.strategy_success_counts,
            "post_attack_successes": post_attack.strategy_success_counts,
            "unique_candidate_groups": post_risk.unique_candidate_groups,
        },
    )
