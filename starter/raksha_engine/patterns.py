"""Structured PII patterns, semantic column/key classification, and text normalization."""
from __future__ import annotations

import re
import unicodedata

# Devanagari digits to ASCII
_DEVA_DIGITS = str.maketrans("०१२३४५६७८९", "0123456789")


def normalize_digits(text: str) -> str:
    return text.translate(_DEVA_DIGITS)


def norm_key(s: str) -> str:
    """Normalize a column header or JSON key for semantic classification."""
    s = unicodedata.normalize("NFKC", s).casefold()
    return re.sub(r"[^a-z0-9\u0900-\u097f]+", " ", s).strip()


# ---------------------------------------------------------------------------
# Semantic column / JSON-key classification
# ---------------------------------------------------------------------------
# Ordered from most specific to least specific.
_COL_RULES: list[tuple[str, re.Pattern[str]]] = [
    ("RELATIVE_NAME", re.compile(r"\b(relative|father|mother|husband|wife|spouse|guardian|son of|daughter of|s o|d o|w o|c o|attendant|care of|nominee|next of kin|pita|pati|mata)\b.*\b(name|naam)?\b|\b(father|mother|husband|wife|spouse|guardian|relative)\b")),
    ("PATIENT_NAME", re.compile(r"\b(patient\s*s?\s*name|beneficiary(\s*name)?|full\s*name|pt\s*name|p\s*name|subscriber\s*name|raised\s*by|contact\s*person|first\s*name|last\s*name|firstname|lastname|surname|given\s*name|naam|नाम|मरीज का नाम)\b|^(?:name|first|last|local)$")),
    ("PHONE", re.compile(r"\b(mobile(\s*no)?|phone|cell|tel|telephone|contact\s*(no|num|number|#)?|callback|whatsapp|मोबाइल|फोन)\b")),
    ("EMAIL", re.compile(r"\b(e?\s*mail|email\s*id|mail\s*id)\b")),
    ("AADHAAR", re.compile(r"\b(aadhaar|aadhar|uidai|आधार)\b")),
    ("ABHA_NUMBER", re.compile(r"\b(abha|health\s*id|ndhm)\b")),
    ("PAN", re.compile(r"\b(pan|payer\s*pan|pan\s*no|pan\s*card)\b")),
    ("INSURANCE_ID", re.compile(r"\b(pmjay|policy\s*(no|num|number|id)?|insurance\s*(id|no|num)?|claim\s*id|tpa\s*id|member\s*id|rsby)\b")),
    ("MRN", re.compile(r"\b(uhid|mrn|patient\s*ref|patient\s*id|patientid|ipd\s*(no|id)?|opd\s*(no|id)?|reg\s*(no|id)|adm\s*(no|id)|bill\s*no|visit\s*id)\b")),
    ("DOB", re.compile(r"\b(dob|date\s*of\s*birth|birth\s*date|born|janm\s*tithi|janm|जन्म\s*तिथि)\b")),
    ("AGE", re.compile(r"\b(age|umar|umr|आयु|उम्र)\b")),
    ("GENDER", re.compile(r"\b(gender|sex|ling|लिंग)\b")),
    ("PIN", re.compile(r"\b(pin(\s*code)?|postal(\s*code)?|zip(\s*code)?|पिन)\b")),
    ("VILLAGE", re.compile(r"\b(village|gram|mohalla|gram\s*mohalla|gaon|city|town|ward|गाँव|ग्राम)\b")),
    ("TEHSIL", re.compile(r"\b(tehsil|taluka|block|sub\s*district|तहसील)\b")),
    ("DISTRICT", re.compile(r"\b(district|distt|dist|jila|zila|जिला)\b")),
    ("HOUSE", re.compile(r"\b(house(\s*no)?|h\s*no|makan(\s*no)?|flat(\s*no)?|door(\s*no)?)\b")),
    ("LOCALITY", re.compile(r"\b(locality|colony|sector|street|road|lane|area|mohalla)\b")),
    ("LANDMARK", re.compile(r"\b(landmark|near|opp|opposite)\b")),
    ("ADDRESS", re.compile(r"\b(address|residential\s*address|permanent\s*address|addr|pata|पता)\b")),
    ("DATE", re.compile(r"\b(date|reg\s*date|registration\s*date|registered|visit\s*date|admission\s*date|discharge\s*date|adm\s*date|disch\s*date|तारीख|दिनांक)\b")),
    ("SOURCE_PATH", re.compile(r"\b(source\s*path|file\s*path|export\s*path|original\s*path)\b")),
    ("DOCTOR", re.compile(r"\b(doctor|physician|consultant|clinician|surgeon|author|dr)\b")),
]

# Columns that must NEVER be redacted as patient PII
CLINICAL_SAFE_COLS = re.compile(
    r"\b(drug|medicine|medication|strength|dose|dosage|dosequantity|form|category|schedule|frequency|duration|route|"
    r"instructions|regimen|diagnosis|icd|snomed|loinc|code|display|procedure|package|complaint|complaints|history|"
    r"vitals|bp|pulse|temp|temperature|spo2|weight|height|bmi|lab|test|panel|specimen|result|value|valuequantity|"
    r"unit|range|reference|normal|allergy|allergies|reaction|severity|onset|encounter|observation|condition|"
    r"department|ward|bed|hospital|system|status|amount|inr|total|visits|count|type|category)\b"
)


def is_clinical_safe_field(name: str) -> bool:
    """Return True if the column/key name is a clinical/numeric field where PIN/Ward regexes must not run."""
    nk = norm_key(name)
    if not nk:
        return False
    return bool(
        CLINICAL_SAFE_COLS.search(nk)
        and not re.search(r"\b(patient|beneficiary|relative|mobile|phone|aadhaar|abha|pan|dob|address|pin|postal)\b", nk)
    )


def classify_field(name: str) -> str | None:
    """Return semantic PII/QI type for a column header or JSON key, or None."""
    nk = norm_key(name)
    if not nk:
        return None
    if CLINICAL_SAFE_COLS.search(nk) and not re.search(r"\b(patient|beneficiary|relative|mobile|phone|aadhaar|abha|pan|dob|address)\b", nk):
        return None
    for kind, rx in _COL_RULES:
        if rx.search(nk):
            return kind
    return None


# ---------------------------------------------------------------------------
# Free-text direct-identifier patterns
# ---------------------------------------------------------------------------
# Note: ORDER MATTERS! Longer/more specific IDs (ABHA 14 digits, Aadhaar 12 digits)
# must be matched before 10-digit phones.

RX_ABHA_NUM = re.compile(r"(?<!\d)(?:91[\s-]?)?\d{2}[\s-]?\d{4}[\s-]?\d{4}[\s-]?\d{4}(?!\d)")
RX_ABHA_ADDR = re.compile(r"\b[a-zA-Z0-9._-]+@(?:abdm|sbx|ndhm)\b", re.IGNORECASE)
RX_AADHAAR = re.compile(r"(?<!\d)\d{4}[\s-]?\d{4}[\s-]?\d{4}(?!\d)")
RX_AADHAAR_MASKED = re.compile(r"(?i)\b[X*]{4}[\s-]?[X*]{4}[\s-]?\d{4}\b")
RX_PHONE = re.compile(r"(?<!\d)(?:\+?91[\s-]?|0)?[6-9]\d{4}[\s-]?\d{5}(?!\d)")
RX_PHONE_MASKED = re.compile(r"(?i)(?<!\d)[6-9]\d[X*]{4,6}\d{2,4}(?!\d)")
RX_EMAIL = re.compile(r"\b[\w.+-]+@[\w-]+\.[\w.-]+\b")
RX_PAN = re.compile(r"\b[A-Z]{5}\d{4}[A-Z]\b")

# Hospital MRN / UHID / IPD / OPD / PMJAY / Policy / Bill IDs
RX_MRN = re.compile(
    r"(?<![A-Za-z0-9])(?:"
    r"(?i:SNJ/\d{2}/\d{4,8})"
    r"|(?i:UHID[-/]?\d{4,10})"
    r"|(?i:JJH[-/]\d{4,10})"
    r"|(?i:DHH[-/]?(?:IPD|OPD|PT)?[-/]?\d{3,8})"
    r"|(?i:ADM\d{5,8})"
    r"|(?i:IP[-/]\d{2}[-/]\d{4,8})"
    r"|(?i:IPD[-/]\d{4}[-/]\d{4,8})"
    r"|(?i:OPD/\d{2}/\d{2}/\d{4,8})"
    r"|(?i:BL/\d{2}/\d{4,8})"
    r"|[A-Z]{2,5}[-/]\d{2,4}[-/]\d{4,8}"
    r")(?![A-Za-z0-9])"
)
RX_INSURANCE = re.compile(
    r"\b(?:"
    r"PMJAY[-/][A-Z]{2}[-/]\d{6,14}"
    r"|POL/\d{2}/\d{5,12}"
    r"|INS[-/]\d{4,12}"
    r"|TPA[-/]\d{4,12}"
    r")\b"
)

# Address & location components
RX_HOUSE = re.compile(r"(?i)(?:\b(?:H\.?\s*No\.?|House(?:\s*No\.?)?|Makan(?:\s*No\.?)?|Flat(?:\s*No\.?)?)\s*[:#-]?\s*\d+[A-Za-z0-9/-]*\b|मकान\s*नं\.?\s*[:#-]?\s*\d+[A-Za-z0-9/-]*)")
RX_LOCALITY = re.compile(r"(?im)(?:\b(?:Ward\s*\d+|Mohalla\s+[A-Z][A-Za-z\s]{2,30}?)(?=\s*(?:,|\n|$|\bTehsil\b|\bDistt\b|\bnear\b|\bopp\b))|(?:वार्ड\s*\d+|मोहल्ला\s+[\u0900-\u097f\s]{2,30}?)(?=\s*(?:,|\n|$|तहसील|जिला)))")
RX_LANDMARK = re.compile(r"(?im)(?:\b(?:near|opp\.?|opposite|behind)\s+[A-Z][A-Za-z\s]{2,35}?(?=\s*(?:,|\n|$|\bTehsil\b|\bDistt\b))|[\u0900-\u097f\s]{2,35}?\s+के\s+(?:पास|पीछे|सामने))")
RX_VILLAGE_LABEL = re.compile(
    r"(?im)(?P<prefix>\b(?:Village|Vill\.?|Gram|Gaon)\s*[:\-]?\s*|(?:ग्राम|गाँव|गांव)\s*[:\-]?\s*)"
    r"(?P<val>[^\n,;|।]+?)(?=\s*(?:,|;|\||।|\n|\bTehsil\b|\bTaluka\b|\bDistt?\b|तहसील|जिला|$))"
)
RX_VILLAGE_BEFORE_TEHSIL = re.compile(
    r"(?im)(?<=,\s)(?!(?:H\.?\s*No|House|Makan|Flat|Ward|Mohalla|near|opp|opposite|behind|C/O|S/o|D/o|W/o)\b)"
    r"(?P<val>[A-Za-z\u0900-\u097f][A-Za-z\u0900-\u097f\s]{2,35}?)(?=\s*,\s*(?:Tehsil|Taluka|Block|तहसील|जिला|Distt?\.?)\b)"
)
RX_PIN = re.compile(
    r"(?<!\d)(?<!-)(?<!\.)[1-8]\d{5}(?!\d)(?!-)(?!\s*(?:/uL|/cumm|/mm3|mg|mcg|ml|mmol|mmhg|g/dl|units|bpm|kg|cm|%)\b)"
)

# Dates: DD/MM/YYYY, DD-MM-YYYY, YYYY-MM-DD, MM/DD/YYYY
RX_DATE_ISO = re.compile(r"\b(19\d{2}|20\d{2})-(0[1-9]|1[0-2])-(0[1-9]|[12]\d|3[01])\b")
RX_DATE_SLASH = re.compile(r"\b(\d{1,2})[/-](\d{1,2})[/-](19\d{2}|20\d{2})\b")

# DOB label
RX_DOB_LABEL = re.compile(
    r"(?i)\b(?:DOB|Date\s+of\s+Birth|Birth\s*Date|जन्म\s*तिथि)\s*[:\-]?\s*(\d{1,2}[/-]\d{1,2}[/-]\d{2,4}|\d{4}-\d{2}-\d{2})"
)
