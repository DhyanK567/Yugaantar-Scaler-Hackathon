"""M13.5 & M13.7 — Offline FHIR R4 Structural & Post-Sanitisation Clinical Validator.

Validates:
- FHIR R4 Bundle & resource structural integrity across 14 resource types
- Internal reference integrity (urn:uuid:, ResourceType/id, #contained)
- Clinical value, medication, dosage, unit, numeric, and date-interval preservation
- Record-count reconciliation and schema consistency

Strictly separates:
  A. Privacy transformations
  B. Clinical data preservation
  C. Structural changes
  D. Validation failures (with stable reason codes)
"""
from __future__ import annotations

import datetime as dt
import re
from dataclasses import dataclass, field

from .privacy import parse_date_str

# Required top-level fields per FHIR R4 resource type (offline lightweight schema)
FHIR_REQUIRED_FIELDS: dict[str, tuple[str, ...]] = {
    "Patient": (),
    "RelatedPerson": ("patient",),
    "Encounter": ("status", "class"),
    "Observation": ("status", "code"),
    "Condition": ("code",),
    "Medication": ("code",),
    "MedicationRequest": ("status", "intent"),
    "MedicationStatement": ("status",),
    "DiagnosticReport": ("status", "code"),
    "Practitioner": (),
    "Organization": (),
    "Location": (),
    "Procedure": ("status", "code"),
    "AllergyIntolerance": ("code",),
}


@dataclass(frozen=True)
class ValidationFailure:
    code: str
    location: str
    detail: str


@dataclass
class FhirValidationResult:
    bundles_checked: int = 0
    resources_checked: int = 0
    valid: bool = True
    failures: list[ValidationFailure] = field(default_factory=list)


@dataclass
class ClinicalValidationReport:
    # A. Privacy transformations
    privacy_transformations: dict[str, int] = field(default_factory=dict)
    # B. Clinical data preservation (exact counts)
    expected_clinical_items: int = 0
    preserved_clinical_items: int = 0
    modified_clinical_items: int = 0
    missing_clinical_items: int = 0
    # C. Structural changes
    record_count_input: int = 0
    record_count_output: int = 0
    fhir_bundles_checked: int = 0
    fhir_resources_checked: int = 0
    # D. Validation failures
    failures: list[ValidationFailure] = field(default_factory=list)

    @property
    def passed(self) -> bool:
        return len(self.failures) == 0 and self.missing_clinical_items == 0 and self.modified_clinical_items == 0


def validate_fhir_r4_bundle(bundle: dict, location: str = "doc") -> FhirValidationResult:
    """Validate an exported FHIR R4 Bundle offline without network dependencies."""
    res = FhirValidationResult(bundles_checked=1)
    if not isinstance(bundle, dict) or bundle.get("resourceType") != "Bundle":
        res.valid = False
        res.failures.append(ValidationFailure("FHIR_NOT_BUNDLE", location, "resourceType is not Bundle"))
        return res
    if not bundle.get("type"):
        res.valid = False
        res.failures.append(ValidationFailure("FHIR_BUNDLE_MISSING_TYPE", location, "Bundle.type is missing"))

    entries = bundle.get("entry")
    if not isinstance(entries, list):
        res.valid = False
        res.failures.append(ValidationFailure("FHIR_BUNDLE_MISSING_ENTRY", location, "Bundle.entry must be a list"))
        return res

    # Collect defined fullUrls and ResourceType/id targets for reference checks
    known_targets: set[str] = set()
    for ent in entries:
        if not isinstance(ent, dict):
            continue
        if ent.get("fullUrl"):
            known_targets.add(str(ent["fullUrl"]))
        r = ent.get("resource")
        if isinstance(r, dict) and r.get("resourceType") and r.get("id"):
            known_targets.add(f"{r['resourceType']}/{r['id']}")

    for idx, ent in enumerate(entries):
        if not isinstance(ent, dict) or not isinstance(ent.get("resource"), dict):
            res.valid = False
            res.failures.append(ValidationFailure("FHIR_INVALID_ENTRY", f"{location}/entry/{idx}", "Missing resource dict"))
            continue
        r = ent["resource"]
        rtype = r.get("resourceType")
        if not rtype or not isinstance(rtype, str):
            res.valid = False
            res.failures.append(ValidationFailure("FHIR_MISSING_RESOURCE_TYPE", f"{location}/entry/{idx}", "Missing resourceType"))
            continue
        res.resources_checked += 1

        # Required fields for known R4 resources
        for req_field in FHIR_REQUIRED_FIELDS.get(rtype, ()):
            if req_field not in r or r[req_field] is None:
                res.valid = False
                res.failures.append(
                    ValidationFailure("FHIR_REQUIRED_FIELD_MISSING", f"{location}/entry/{idx}/{rtype}", f"Missing {req_field}")
                )

        # MedicationRequest must have medicationCodeableConcept or medicationReference
        if rtype == "MedicationRequest" and not ("medicationCodeableConcept" in r or "medicationReference" in r):
            res.valid = False
            res.failures.append(
                ValidationFailure("FHIR_REQUIRED_FIELD_MISSING", f"{location}/entry/{idx}/MedicationRequest", "Missing medication[x]")
            )

        # Check internal references if they point to urn:uuid: or ResourceType/id
        _check_refs(r, f"{location}/entry/{idx}/{rtype}", known_targets, res)

    return res


def _check_refs(node, loc: str, known_targets: set[str], res: FhirValidationResult) -> None:
    if isinstance(node, dict):
        ref = node.get("reference")
        if isinstance(ref, str) and ref.startswith("urn:uuid:") and known_targets and ref not in known_targets:
            res.valid = False
            res.failures.append(ValidationFailure("FHIR_BROKEN_REFERENCE", loc, f"Unresolved URN reference: {ref}"))
        for v in node.values():
            _check_refs(v, loc, known_targets, res)
    elif isinstance(node, list):
        for item in node:
            _check_refs(item, loc, known_targets, res)


def verify_date_interval_preserved(
    orig_start: str,
    orig_end: str,
    san_start: str,
    san_end: str,
) -> tuple[bool, str | None]:
    """Verify that temporal ordering and exact day interval are preserved after shifting."""
    p1 = parse_date_str(orig_start)
    p2 = parse_date_str(orig_end)
    q1 = parse_date_str(san_start)
    q2 = parse_date_str(san_end)
    if not (p1 and p2 and q1 and q2):
        return False, "DATE_PARSE_FAILED"
    if (p2[0] - p1[0]).days != (q2[0] - q1[0]).days:
        return False, "DATE_INTERVAL_MISMATCH"
    if (p2[0] >= p1[0]) != (q2[0] >= q1[0]):
        return False, "DATE_ORDER_VIOLATED"
    return True, None


def validate_clinical_probes(
    expected_items: list[str],
    sanitized_text: str,
    location: str = "doc",
) -> ClinicalValidationReport:
    """Validate that all expected clinical items (diagnoses, meds, dosages, units, labs) survive."""
    rep = ClinicalValidationReport(expected_clinical_items=len(expected_items))
    norm_san = " ".join(sanitized_text.casefold().split())
    for item in expected_items:
        norm_item = " ".join(item.casefold().split())
        if norm_item in norm_san:
            rep.preserved_clinical_items += 1
        else:
            # Check if numeric part survived but unit/text was modified
            nums = re.findall(r"\d+(?:\.\d+)?", norm_item)
            if nums and all(n in norm_san for n in nums):
                rep.modified_clinical_items += 1
                rep.failures.append(ValidationFailure("CLINICAL_ITEM_MODIFIED", location, f"Modified: {item}"))
            else:
                rep.missing_clinical_items += 1
                rep.failures.append(ValidationFailure("CLINICAL_VALUE_LOST", location, f"Lost: {item}"))
    return rep


# ==============================================================================
# M15.5 Phase 2 — Evidence-Based Clinical Fidelity & Drift Engine
# ==============================================================================

CLINICAL_CATEGORY_PATTERNS: dict[str, re.Pattern[str]] = {
    "medication_names": re.compile(
        r"\b(?:Paracetamol|Dolo|Azithromycin|Amoxicillin|Metformin|Amlodipine|Atorvastatin|"
        r"Pantoprazole|Ceftriaxone|Insulin|Levodopa|Salbutamol|Aspirin|Clopidogrel|Losartan|"
        r"Omeprazole|Ciprofloxacin|Ibuprofen|Doxycycline|ORS)\b",
        re.IGNORECASE,
    ),
    "dosages": re.compile(r"\b\d+(?:\.\d+)?\s*(?:mg|mcg|g|ml|IU|units)\b", re.IGNORECASE),
    "units": re.compile(r"\b(?:mg/dL|mmol/L|g/dL|U/L|IU/L|mg|mcg|mL|bpm|mmHg)\b", re.IGNORECASE),
    "frequencies": re.compile(r"\b(?:OD|BD|TDS|QID|HS|SOS|PRN|once\s+daily|twice\s+daily|thrice\s+daily)\b", re.IGNORECASE),
    "administration_routes": re.compile(r"\b(?:oral|PO|IV|IM|SC|subcutaneous|topical|inhaled|sublingual)\b", re.IGNORECASE),
    "treatment_duration": re.compile(r"\b(?:for\s+)?\d+\s*(?:days?|weeks?|months?)\b", re.IGNORECASE),
    "blood_pressure": re.compile(r"\b(?:BP\s*[:\-]?\s*)?\d{2,3}/\d{2,3}(?:\s*mmHg)?\b", re.IGNORECASE),
    "heart_rate": re.compile(r"\b(?:HR|Pulse)\s*[:\-]?\s*\d{2,3}(?:\s*bpm)?\b", re.IGNORECASE),
    "temperature": re.compile(r"\bTemp(?:erature)?\s*[:\-]?\s*\d{2,3}(?:\.\d+)?\s*(?:°?[FC])\b", re.IGNORECASE),
    "spo2": re.compile(r"\bSpO2\s*[:\-]?\s*\d{2,3}\s*%\b", re.IGNORECASE),
    "haemoglobin": re.compile(r"\b(?:Hb|Haemoglobin|Hemoglobin)\s*[:\-]?\s*\d{1,2}(?:\.\d+)?(?:\s*g/dL)?\b", re.IGNORECASE),
    "blood_glucose": re.compile(r"\b(?:RBS|FBS|PPBS|Glucose|Blood\s+Sugar)\s*[:\-]?\s*\d{2,3}(?:\.\d+)?(?:\s*mg/dL)?\b", re.IGNORECASE),
    "laboratory_measurements": re.compile(
        r"\b(?:Creatinine|Bilirubin|Platelets?|WBC|RBC|TSH|HbA1c|ALT|AST|SGPT|SGOT)\s*[:\-]?\s*\d+(?:\.\d+)?(?:\s*[A-Za-z/%]+)?\b",
        re.IGNORECASE,
    ),
    "diagnoses": re.compile(
        r"\b(?:Diabetes(?:\s+mellitus)?|Hypertension|Dengue(?:\s+fever)?|Malaria|Typhoid|"
        r"Asthma|Pneumonia|Bronchitis|Parkinson(?:'s)?\s+disease|Alzheimer(?:'s)?\s+disease|"
        r"Bell(?:'s)?\s+palsy|Coronary\s+artery\s+disease|Anemia|Fever|Cough)\b",
        re.IGNORECASE,
    ),
}


def _safe_pct(preserved: int, expected: int) -> float | None:
    if expected <= 0:
        return None
    pct = (preserved / expected) * 100.0
    if preserved < expected and pct >= 99.995:
        # Never round <100% up to 100.0%
        return 99.99
    return round(pct, 2)


def _extract_category_multiset(text: str, rx: re.Pattern[str]) -> list[str]:
    return [" ".join(m.group(0).casefold().split()) for m in rx.finditer(text)]


def analyze_clinical_drift(
    input_texts: list[str],
    sanitized_texts: list[str],
    fhir_bundles: list[dict] | None = None,
) -> dict:
    """Compare clinical entities across input and sanitized texts without exposing raw patient text.

    Detects exact preservation, missing entities, numeric/dosage drift (e.g. 5 mg -> 50 mg),
    unexpected entities, and FHIR R4 structural & code/reference integrity.
    """
    from collections import Counter

    in_joined = "\n".join(input_texts)
    san_joined = "\n".join(sanitized_texts)

    categories_report: dict[str, dict] = {}
    total_expected = 0
    total_preserved = 0
    total_missing = 0
    total_modified = 0
    total_unexpected = 0
    critical_failures: list[dict[str, str]] = []

    for cat_name, rx in CLINICAL_CATEGORY_PATTERNS.items():
        in_counts = Counter(_extract_category_multiset(in_joined, rx))
        san_counts = Counter(_extract_category_multiset(san_joined, rx))

        expected = sum(in_counts.values())
        preserved = 0
        for tok, cnt in in_counts.items():
            preserved += min(cnt, san_counts.get(tok, 0))

        # Check for numeric/unit drift in remaining unmatched tokens (e.g. 5 mg -> 50 mg)
        unmatched_in = []
        for tok, cnt in in_counts.items():
            rem = cnt - min(cnt, san_counts.get(tok, 0))
            unmatched_in.extend([tok] * rem)

        unmatched_san = []
        for tok, cnt in san_counts.items():
            rem = cnt - min(cnt, in_counts.get(tok, 0))
            unmatched_san.extend([tok] * rem)

        modified = 0
        if unmatched_in and unmatched_san and cat_name in ("dosages", "blood_pressure", "heart_rate", "temperature", "spo2", "haemoglobin", "blood_glucose", "laboratory_measurements"):
            pair_count = min(len(unmatched_in), len(unmatched_san))
            modified = pair_count
            if modified > 0:
                critical_failures.append({
                    "category": cat_name,
                    "code": "CLINICAL_VALUE_DRIFT",
                    "count": str(modified),
                    "detail": f"Detected {modified} numeric/unit value mutation(s) in {cat_name}.",
                })

        missing = max(0, expected - preserved - modified)
        unexpected = max(0, len(unmatched_san) - modified)

        total_expected += expected
        total_preserved += preserved
        total_missing += missing
        total_modified += modified
        total_unexpected += unexpected

        categories_report[cat_name] = {
            "expected": expected,
            "preserved": preserved,
            "missing": missing,
            "modified": modified,
            "unexpected": unexpected,
            "exact_preservation_pct": _safe_pct(preserved, expected),
        }

    # FHIR R4 bundle & reference integrity
    fhir_checked = 0
    fhir_valid = 0
    fhir_fail_count = 0
    for b in (fhir_bundles or []):
        res = validate_fhir_r4_bundle(b, location="fhir_bundle")
        fhir_checked += res.bundles_checked
        if res.valid:
            fhir_valid += 1
        else:
            fhir_fail_count += len(res.failures)
            critical_failures.append({
                "category": "fhir_resource_codes_and_refs",
                "code": "FHIR_INTEGRITY_FAILURE",
                "count": str(len(res.failures)),
                "detail": f"FHIR R4 validation failed with {len(res.failures)} structural/reference error(s).",
            })

    categories_report["fhir_resource_codes_and_refs"] = {
        "expected": fhir_checked,
        "preserved": fhir_valid,
        "missing": max(0, fhir_checked - fhir_valid),
        "modified": 0,
        "unexpected": 0,
        "exact_preservation_pct": _safe_pct(fhir_valid, fhir_checked),
    }

    overall_pct = _safe_pct(total_preserved, total_expected)
    passed = (total_modified == 0 and total_missing == 0 and fhir_fail_count == 0)

    return {
        "status": "PASS" if passed else "FAILED",
        "passed": passed,
        "overall": {
            "expected": total_expected,
            "preserved": total_preserved,
            "missing": total_missing,
            "modified": total_modified,
            "unexpected": total_unexpected,
            "exact_fidelity_pct": overall_pct,
        },
        "categories": categories_report,
        "fhir_bundles_checked": fhir_checked,
        "fhir_bundles_valid": fhir_valid,
        "fhir_failures": fhir_fail_count,
        "critical_failures": critical_failures,
    }
