"""Structured PII patterns, semantic column/key classification, and text normalization.
Hardened for multilingual Indian scripts, transliterations, and medical context safety.
"""
from __future__ import annotations

import re
import unicodedata
from .normalizer import DEVA_TO_ASCII_DIGITS, normalize_digits

# ---------------------------------------------------------------------------
# Semantic column / JSON-key classification (English, Hindi, Hinglish)
# ---------------------------------------------------------------------------
def norm_key(s: str) -> str:
    """Normalize a column header or JSON key for semantic classification."""
    s = unicodedata.normalize("NFKC", s).casefold()
    return re.sub(r"[^a-z0-9\u0900-\u097f]+", " ", s).strip()


# Ordered from most specific to least specific.
_COL_RULES: list[tuple[str, re.Pattern[str]]] = [
    (
        "RELATIVE_NAME",
        re.compile(
            r"\b(relative|father|mother|husband|wife|spouse|guardian|son of|daughter of|s o|d o|w o|c o|"
            r"care of|attendant|caregiver|witness|nominee|next of kin|pita|pati|mata|beta|beti|shauhar|biwi|walad|"
            r"पिता|माता|पति|पत्नी|पुत्र|पुत्री|बेटा|बेटी|अभिभावक|परिचारक|गवाह)\b.*\b(name|naam|नाम)?\b|"
            r"\b(father|mother|husband|wife|spouse|guardian|relative|पिता|माता|पति|पत्नी)\b"
        ),
    ),
    (
        "PATIENT_NAME",
        re.compile(
            r"\b(patient\s*s?\s*name|beneficiary(\s*name)?|full\s*name|pt\s*name|p\s*name|subscriber\s*name|"
            r"raised\s*by|contact\s*person|first\s*name|last\s*name|firstname|lastname|surname|given\s*name|"
            r"naam|नाम|मरीज\s*का\s*नाम|रोगी\s*का\s*नाम)\b|^(?:name|first|last|local|naam|नाम)$"
        ),
    ),
    (
        "PHONE",
        re.compile(
            r"\b(mobile(\s*no)?|phone|cell|tel|telephone|contact\s*(no|num|number|#)?|callback|whatsapp|"
            r"मोबाइल|फोन|दूरभाष)\b"
        ),
    ),
    ("EMAIL", re.compile(r"\b(e?\s*mail|email\s*id|mail\s*id|ईमेल)\b")),
    ("AADHAAR", re.compile(r"\b(aadhaar|aadhar|uidai|आधार|आधार\s*कार्ड)\b")),
    ("ABHA_NUMBER", re.compile(r"\b(abha|health\s*id|ndhm|आभा)\b")),
    ("PAN", re.compile(r"\b(pan|payer\s*pan|pan\s*no|pan\s*card|पैन)\b")),
    (
        "INSURANCE_ID",
        re.compile(
            r"\b(pmjay|policy\s*(no|num|number|id)?|insurance\s*(id|no|num)?|claim\s*id|tpa\s*id|member\s*id|rsby|बीमा)\b"
        ),
    ),
    (
        "MRN",
        re.compile(
            r"\b(uhid|mrn|patient\s*ref|patient\s*id|patientid|ipd\s*(no|id)?|opd\s*(no|id)?|reg\s*(no|id)|"
            r"adm\s*(no|id)|bill\s*no|visit\s*id|पंजीकरण\s*संख्या)\b"
        ),
    ),
    ("DOB", re.compile(r"\b(dob|date\s*of\s*birth|birth\s*date|born|janm\s*tithi|janm|जन्म\s*तिथि|जन्म\s*दिनांक)\b")),
    ("AGE", re.compile(r"\b(age|umar|umr|आयु|उम्र)\b")),
    ("GENDER", re.compile(r"\b(gender|sex|ling|लिंग)\b")),
    ("PIN", re.compile(r"\b(pin(\s*code)?|postal(\s*code)?|zip(\s*code)?|पिन|पिन\s*कोड)\b")),
    ("VILLAGE", re.compile(r"\b(village|gram|mohalla|gram\s*mohalla|gaon|city|town|ward|गाँव|गांव|ग्राम)\b")),
    ("TEHSIL", re.compile(r"\b(tehsil|taluka|block|sub\s*district|तहसील|तालुका|ब्लॉक)\b")),
    ("DISTRICT", re.compile(r"\b(district|distt|dist|jila|zila|जिला)\b")),
    ("HOUSE", re.compile(r"\b(house(\s*no)?|h\s*no|makan(\s*no)?|flat(\s*no)?|door(\s*no)?|मकान|मकान\s*नं)\b")),
    ("LOCALITY", re.compile(r"\b(locality|colony|sector|street|road|lane|area|mohalla|मोहल्ला|वार्ड)\b")),
    ("LANDMARK", re.compile(r"\b(landmark|near|opp|opposite|के\s*पास)\b")),
    ("ADDRESS", re.compile(r"\b(address|residential\s*address|permanent\s*address|addr|pata|पता|निवास\s*पता)\b")),
    (
        "DATE",
        re.compile(
            r"\b(date|reg\s*date|registration\s*date|registered|visit\s*date|admission\s*date|discharge\s*date|"
            r"adm\s*date|disch\s*date|तारीख|दिनांक)\b"
        ),
    ),
    ("SOURCE_PATH", re.compile(r"\b(source\s*path|file\s*path|export\s*path|original\s*path)\b")),
    ("DOCTOR", re.compile(r"\b(doctor|physician|consultant|clinician|surgeon|author|dr|डॉक्टर|डॉ)\b")),
]

# Columns that must NEVER be redacted as patient PII
CLINICAL_SAFE_COLS = re.compile(
    r"\b(drug|medicine|medication|strength|dose|dosage|form|category|schedule|frequency|duration|"
    r"diagnosis|icd|code|display|procedure|package|complaint|complaints|history|vitals|bp|pulse|"
    r"temp|temperature|spo2|weight|height|bmi|lab|test|result|value|unit|range|reference|normal|"
    r"department|ward|bed|hospital|system|status|amount|inr|total|visits|count|type|category|"
    r"दवा|खुराक|निदान|लक्षण|जांच|परिणाम|वार्ड|अस्पताल)\b"
)


def is_clinical_safe_field(name: str) -> bool:
    """Return True if the column/key name is a clinical/numeric field where PIN/Ward regexes must not run."""
    nk = norm_key(name)
    if not nk:
        return False
    return bool(
        CLINICAL_SAFE_COLS.search(nk)
        and not re.search(
            r"\b(patient|beneficiary|relative|mobile|phone|aadhaar|abha|pan|dob|address|pin|postal)\b",
            nk,
        )
    )


def classify_field(name: str) -> str | None:
    """Return semantic PII/QI type for a column header or JSON key, or None."""
    nk = norm_key(name)
    if not nk:
        return None
    if CLINICAL_SAFE_COLS.search(nk) and not re.search(
        r"\b(patient|beneficiary|relative|mobile|phone|aadhaar|abha|pan|dob|address)\b", nk
    ):
        return None
    for kind, rx in _COL_RULES:
        if rx.search(nk):
            return kind
    return None


# ---------------------------------------------------------------------------
# Free-text direct-identifier patterns (multilingual & variation-tolerant)
# ---------------------------------------------------------------------------

# ABHA: 14 digits with optional 91 prefix
RX_ABHA_NUM = re.compile(r"(?<!\d)(?:(?:\+?91[\s-]?)?\d{2}[\s-]?)?\d{2}[\s-]?\d{4}[\s-]?\d{4}[\s-]?\d{4}(?!\d)")
RX_ABHA_ADDR = re.compile(r"\b[a-zA-Z0-9._-]+@(?:abdm|sbx|ndhm)\b", re.IGNORECASE)

# Aadhaar: 12 digits, grouped or continuous
RX_AADHAAR = re.compile(r"(?<!\d)\d{4}[\s-]?\d{4}[\s-]?\d{4}(?!\d)")
RX_AADHAAR_MASKED = re.compile(r"(?i)\b[X*]{4}[\s-]?[X*]{4}[\s-]?\d{4}\b")

# Phone numbers: 10 digits starting with 6-9, optional +91, 0, or parentheses
RX_PHONE = re.compile(r"(?<!\d)(?:(?:\+?91[\s-]?|\(?0\)?[\s-]?)|\(\+?91\)\s*)?[6-9]\d{4}[\s-]?\d{5}(?!\d)")
RX_PHONE_MASKED = re.compile(r"(?i)(?<!\d)[6-9]\d[X*]{4,6}\d{2,4}(?!\d)")

# Email and PAN
RX_EMAIL = re.compile(r"\b[\w.+-]+@[\w-]+\.[\w.-]+\b")
RX_PAN = re.compile(r"\b[A-Z]{5}\d{4}[A-Z]\b")

# Hospital MRN / UHID / IPD / OPD / PMJAY / Policy / Bill IDs
RX_MRN = re.compile(
    r"(?<![A-Za-z0-9])(?:"
    r"(?i:SNJ[-/]\d{2}[-/]\d{4,8})"
    r"|(?i:UHID[-/]?\d{4,10})"
    r"|(?i:JJH[-/]\d{4,10})"
    r"|(?i:DHH[-/]?(?:IPD|OPD|PT)?[-/]?\d{3,8})"
    r"|(?i:ADM\d{5,8})"
    r"|(?i:IP[-/]\d{2}[-/]\d{4,8})"
    r"|(?i:IPD[-/]\d{4}[-/]\d{4,8})"
    r"|(?i:OPD[-/]\d{2}[-/]\d{2}[-/]\d{4,8})"
    r"|(?i:BL[-/]\d{2}[-/]\d{4,8})"
    r"|[A-Z]{2,5}[-/]\d{2,4}[-/]\d{4,8}"
    r")(?![A-Za-z0-9])"
)

RX_INSURANCE = re.compile(
    r"\b(?:"
    r"PMJAY[-/][A-Z]{2}[-/]\d{6,14}"
    r"|POL/\d{2}/\d{5,12}"
    r"|INS[-/]\d{4,12}"
    r"|TPA[-/]\d{4,12}"
    r"|RSBY[-/]\d{4,12}"
    r")\b"
)

# Address & location components
RX_HOUSE = re.compile(
    r"(?i)(?:\b(?:H\.?\s*No\.?|House(?:\s*No\.?)?|Makan(?:\s*No\.?)?|Flat(?:\s*No\.?)?|Door(?:\s*No\.?)?)\s*[:#-]?\s*\d+[A-Za-z0-9/-]*\b|"
    r"(?:मकान|घर)\s*(?:नं\.?|नंबर)?\s*[:#-]?\s*\d+[A-Za-z0-9/-]*)"
)

RX_LOCALITY = re.compile(
    r"(?im)(?:\b(?:Ward\s*\d+|Mohalla\s+[A-Z][A-Za-z\s]{2,30}?)(?=\s*(?:,|\n|$|\bTehsil\b|\bDistt\b|\bnear\b|\bopp\b))|"
    r"(?:वार्ड\s*\d+|मोहल्ला\s+[\u0900-\u097f\s]{2,30}?)(?=\s*(?:,|\n|$|तहसील|जिला)))"
)

RX_LANDMARK = re.compile(
    r"(?im)(?:\b(?:near|opp\.?|opposite|behind)\s+[A-Z][A-Za-z\s]{2,35}?(?=\s*(?:,|\n|$|\bTehsil\b|\bDistt\b))|"
    r"[\u0900-\u097f\s]{2,35}?\s+के\s+(?:पास|पीछे|सामने))"
)

RX_VILLAGE_LABEL = re.compile(
    r"(?im)(?P<prefix>\b(?:Village|Vill\.?|Gram|Gaon)\s*[:\-]?\s*|(?:ग्राम|गाँव|गांव)\s*[:\-]?\s*)"
    r"(?P<val>[^\n,;|।]+?)(?=\s*(?:,|;|\||।|\n|\bTehsil\b|\bTaluka\b|\bDistt?\b|तहसील|जिला|$))"
)

RX_VILLAGE_BEFORE_TEHSIL = re.compile(
    r"(?im)(?<=,\s)(?!(?:H\.?\s*No|House|Makan|Flat|Ward|Mohalla|near|opp|opposite|behind|C/O|S/o|D/o|W/o)\b)"
    r"(?P<val>[A-Za-z\u0900-\u097f][A-Za-z\u0900-\u097f\s]{2,35}?)(?=\s*,\s*(?:Tehsil|Taluka|Block|तहसील|जिला|Distt?\.?)\b)"
)

# PIN Code: 6 digits starting with 1-8 (must not be part of a dosage or medical measurement)
RX_PIN = re.compile(r"(?<!\d)(?<!-)[1-8]\d{5}(?!\d)(?!-)")

# Dates: DD/MM/YYYY, DD-MM-YYYY, YYYY-MM-DD
RX_DATE_ISO = re.compile(r"\b(19\d{2}|20\d{2})-(0[1-9]|1[0-2])-(0[1-9]|[12]\d|3[01])\b")
RX_DATE_SLASH = re.compile(r"\b(\d{1,2})[/-](\d{1,2})[/-](19\d{2}|20\d{2})\b")

# DOB label: DOB, Date of Birth, जन्म तिथि
RX_DOB_LABEL = re.compile(
    r"(?i)\b(?:DOB|Date\s+of\s+Birth|Birth\s*Date|जन्म\s*तिथि|जन्म\s*तारीख)\s*[:\-]?\s*(\d{1,2}[/-]\d{1,2}[/-]\d{2,4}|\d{4}-\d{2}-\d{2})"
)


def extract_free_text_identifiers(text: str) -> list[dict[str, any]]:
    """Scan free text for direct identifiers (ABHA, Aadhaar, PAN, Phone, Email, MRN).
    Normalizes Devanagari numerals to ASCII before digit-based regex evaluation.
    """
    matches: list[dict[str, any]] = []

    # Map Devanagari digits to ASCII for pattern matching while keeping track of text
    norm_digits_text = text.translate(DEVA_TO_ASCII_DIGITS)

    for m in RX_ABHA_NUM.finditer(norm_digits_text):
        val = m.group(0).strip()
        # Avoid pure 10-digit phones or non-ABHA
        d_count = sum(c.isdigit() for c in val)
        if d_count in (14, 16):
            matches.append({"entity_type": "ABHA_NUMBER", "value": text[m.start():m.end()], "start": m.start(), "end": m.end()})

    for m in RX_AADHAAR.finditer(norm_digits_text):
        val = m.group(0).strip()
        d_count = sum(c.isdigit() for c in val)
        if d_count == 12:
            matches.append({"entity_type": "AADHAAR", "value": text[m.start():m.end()], "start": m.start(), "end": m.end()})

    for m in RX_PAN.finditer(text):
        matches.append({"entity_type": "PAN", "value": m.group(0), "start": m.start(), "end": m.end()})

    for m in RX_PHONE.finditer(norm_digits_text):
        matches.append({"entity_type": "PHONE", "value": text[m.start():m.end()], "start": m.start(), "end": m.end()})

    for m in RX_EMAIL.finditer(text):
        matches.append({"entity_type": "EMAIL", "value": m.group(0), "start": m.start(), "end": m.end()})

    for m in RX_MRN.finditer(text):
        matches.append({"entity_type": "MRN", "value": m.group(0), "start": m.start(), "end": m.end()})

    return matches

