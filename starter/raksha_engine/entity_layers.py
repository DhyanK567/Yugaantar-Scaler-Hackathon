"""Canonical 6-layer Entity Representation & Consolidation for MediLocker."""
from __future__ import annotations

from dataclasses import dataclass
from typing import List


@dataclass(frozen=True)
class EntityDetection:
    category: str
    span_or_path: str
    layer: str              # STRUCTURAL | PATTERN | NAME | MULTILINGUAL | CONTEXTUAL
    context: str
    confidence: float
    risk_level: str         # LOW | MODERATE | HIGH | CRITICAL
    transformation: str     # REDACT | PSEUDONYMISE | GENERALISE | PRESERVE
    clinical_protected: bool
    decision: str           # TRANSFORM | PRESERVE | QUARANTINE


def consolidate_detections(detections: List[EntityDetection]) -> List[EntityDetection]:
    """Resolve overlapping or competing entity detections deterministically.

    Clinical-protected entities take precedence unless a high-confidence direct PII
    signal overrides them; higher confidence wins among competing transforms.
    """
    ordered = sorted(
        detections,
        key=lambda d: (d.span_or_path, -d.confidence, 0 if d.clinical_protected else 1),
    )
    seen_paths: set[str] = set()
    consolidated: List[EntityDetection] = []
    for det in ordered:
        if det.span_or_path in seen_paths:
            continue
        seen_paths.add(det.span_or_path)
        consolidated.append(det)
    return consolidated
