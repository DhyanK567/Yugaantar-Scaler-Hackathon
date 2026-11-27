"""M10.1 — Deterministic 5-tier Quasi-Identifier & Field Classification Layer.

Classifies structured column headers and JSON keys (English, Hindi, Hinglish) into:
  A. DIRECT_IDENTIFIER   - Directly identifies an individual (name, phone, Aadhaar, ABHA, MRN, DOB, etc.)
  B. QUASI_IDENTIFIER    - Indirectly identifies via combinations (age, gender, village, PIN, dept, dates, LOS)
  C. SENSITIVE_CLINICAL  - Sensitive medical/diagnosis/treatment attributes to preserve (not redact)
  D. CLINICAL_UTILITY    - Clinical measurements/vitals/labs/meds/dosages to strictly preserve
  E. SAFE_METADATA       - Operational/schema metadata safe to retain
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from enum import Enum

from .patterns import classify_field, is_clinical_safe_field, norm_key


class FieldCategory(str, Enum):
    DIRECT_IDENTIFIER = "A_DIRECT_IDENTIFIER"
    QUASI_IDENTIFIER = "B_QUASI_IDENTIFIER"
    SENSITIVE_CLINICAL = "C_SENSITIVE_CLINICAL"
    CLINICAL_UTILITY = "D_CLINICAL_UTILITY"
    SAFE_METADATA = "E_SAFE_METADATA"


@dataclass(frozen=True)
class FieldClassification:
    field_name: str
    category: FieldCategory
    semantic_kind: str
    reason_code: str


_DIRECT_KINDS = {
    "PATIENT_NAME", "RELATIVE_NAME", "PHONE", "EMAIL", "AADHAAR",
    "ABHA_NUMBER", "PAN", "INSURANCE_ID", "MRN", "DOB", "HOUSE", "SOURCE_PATH",
}

_QUASI_KINDS = {
    "AGE", "GENDER", "PIN", "VILLAGE", "TEHSIL", "DISTRICT",
    "LOCALITY", "LANDMARK", "ADDRESS", "DATE",
}

_RX_LOS = re.compile(r"\b(los|length\s*of\s*stay|stay\s*days|days\s*admitted|bharti\s*din)\b")
_RX_HOSP_DEPT = re.compile(r"\b(hospital|facility|clinic|department|dept|ward|unit|vibhag|विभाग|अस्पताल)\b")
_RX_SENSITIVE_CLINICAL = re.compile(
    r"\b(diagnosis|diagnoses|icd|icd10|condition|comorbidity|disease|rog|bimari|बीमारी|"
    r"treatment|procedure|surgery|therapy|medication|medicine|drug|rx|prescription|dawai|दवा)\b"
)
_RX_CLINICAL_UTILITY = re.compile(
    r"\b(bp|blood\s*pressure|pulse|temp|temperature|spo2|weight|height|bmi|vitals|"
    r"dose|dosage|strength|frequency|duration|form|lab|test|result|value|unit|range|reference|"
    r"complaint|complaints|history|notes|remarks|summary|clinical)\b"
)
_RX_SAFE_META = re.compile(
    r"\b(resourcetype|id|status|system|profile|version|schema|contenttype|type|category|"
    r"generated|week|count|visits|amount|inr|total|code|display)\b"
)


def classify_field_tier(field_name: str) -> FieldClassification:
    """Classify a field/header name deterministically into one of 5 privacy tiers."""
    nk = norm_key(field_name)
    if not nk:
        return FieldClassification(field_name, FieldCategory.SAFE_METADATA, "UNKNOWN", "META_EMPTY_KEY")

    # 1. Clinical utility & sensitive clinical checks (never confuse vitals/meds/diagnoses with PII)
    if _RX_SENSITIVE_CLINICAL.search(nk) and not re.search(r"\b(patient|relative|name|dob|phone)\b", nk):
        kind = "DIAGNOSIS" if re.search(r"\b(diagnosis|diagnoses|icd|condition|disease|rog|bimari)\b", nk) else "TREATMENT"
        return FieldClassification(field_name, FieldCategory.SENSITIVE_CLINICAL, kind, f"SENSITIVE_{kind}")

    if _RX_CLINICAL_UTILITY.search(nk) and not re.search(r"\b(patient|relative|name|dob|phone|address)\b", nk):
        return FieldClassification(field_name, FieldCategory.CLINICAL_UTILITY, "CLINICAL_VALUE", "CLINICAL_PRESERVE")

    # 2. Reuse patterns.classify_field for direct & quasi identifiers
    kind = classify_field(field_name)
    if kind in _DIRECT_KINDS:
        return FieldClassification(field_name, FieldCategory.DIRECT_IDENTIFIER, kind, f"DIRECT_{kind}")
    if kind in _QUASI_KINDS:
        return FieldClassification(field_name, FieldCategory.QUASI_IDENTIFIER, kind, f"QI_{kind}")

    # 3. Additional quasi-identifiers: LOS, hospital/department
    if _RX_LOS.search(nk):
        return FieldClassification(field_name, FieldCategory.QUASI_IDENTIFIER, "LENGTH_OF_STAY", "QI_LENGTH_OF_STAY")
    if _RX_HOSP_DEPT.search(nk):
        return FieldClassification(field_name, FieldCategory.QUASI_IDENTIFIER, "HOSPITAL_DEPT", "QI_HOSPITAL_DEPT")

    # 4. Doctor / clinical safe fallback
    if kind == "DOCTOR":
        return FieldClassification(field_name, FieldCategory.SAFE_METADATA, "DOCTOR", "META_CLINICIAN_ROLE")
    if is_clinical_safe_field(field_name):
        return FieldClassification(field_name, FieldCategory.CLINICAL_UTILITY, "CLINICAL_SAFE", "CLINICAL_SAFE_COL")
    if _RX_SAFE_META.search(nk):
        return FieldClassification(field_name, FieldCategory.SAFE_METADATA, "METADATA", "META_OPERATIONAL")

    return FieldClassification(field_name, FieldCategory.SAFE_METADATA, "GENERAL", "META_DEFAULT")
