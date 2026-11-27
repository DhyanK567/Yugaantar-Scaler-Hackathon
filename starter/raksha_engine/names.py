"""Multilingual (English, Hindi/Devanagari, Hinglish) name & relationship detection engine
with strict medical-context preservation guards and cross-script transliteration learning.
"""
from __future__ import annotations

import re
import unicodedata
from .normalizer import (
    deva_to_latin,
    is_devanagari,
    normalize_multilingual_text,
    phonetic_norm,
    strip_honorifics,
)


def normalize_name_tokens(name: str, keep_initials: bool = False) -> list[str]:
    """Return normalized phonetic tokens for a person name (excluding honorifics).

    Supports Devanagari, Hinglish, zero-width stripping, and 'Surname, First M.' ordering.
    """
    s = unicodedata.normalize("NFKC", name)
    s = re.sub(r"[\u200b-\u200d\ufeff]", "", s).casefold()
    if any("\u0900" <= c <= "\u097f" for c in s):
        s = deva_to_latin(s)
    # Handle "Surname, Given Middle" format
    if "," in s:
        parts = [p.strip() for p in s.split(",", 1)]
        if len(parts) == 2 and parts[0] and parts[1]:
            s = f"{parts[1]} {parts[0]}"
    # Expand common abbreviations before stripping punctuation
    s = re.sub(r"\b(?:mohd|md)\.?\b", "mohammad", s)
    s = re.sub(r"\b(?:smt|shri|dr|mr|mrs|ms|km)\.?\b", " ", s)
    raw_tokens = re.findall(r"[a-z]+", s)
    out = []
    min_len = 1 if keep_initials else 2
    for tok in raw_tokens:
        if tok in {"ji", "sahab", "saheb", "behenji", "bhaiya", "didi", "bhai"}:
            continue
        p = phonetic_norm(tok)
        if len(p) >= min_len:
            out.append(p)
    if not out:
        out = [phonetic_norm(t) for t in raw_tokens if len(t) >= min_len]
    return out

def names_match_with_initials(toks_a: list[str], toks_b: list[str]) -> bool:
    """Return True if two token lists represent the same name allowing initials
    (e.g. ['r', 'k', 'werma'] vs ['rajes', 'kumar', 'werma']) and matching surname.
    """
    if not toks_a or not toks_b:
        return False
    # Surname (last token) must match or be very close
    if toks_a[-1] != toks_b[-1]:
        return False
    if len(toks_a) < 2 or len(toks_b) < 2:
        return False
    # Compare given/middle tokens allowing 1-char initial prefix match
    g_a, g_b = toks_a[:-1], toks_b[:-1]
    if len(g_a) != len(g_b):
        # Allow "R. Kumar" vs "Rajesh Kumar" if first initial matches
        return len(g_a[0]) == 1 and g_b[0].startswith(g_a[0]) or len(g_b[0]) == 1 and g_a[0].startswith(g_b[0])
    for ta, tb in zip(g_a, g_b):
        if ta == tb:
            continue
        if len(ta) == 1 and tb.startswith(ta):
            continue
        if len(tb) == 1 and ta.startswith(tb):
            continue
        return False
    return True


# ---------------------------------------------------------------------------
# Medical-context preserve guards
# ---------------------------------------------------------------------------
# Clinical words that must NEVER be treated as person names
CLINICAL_STOPWORDS = {
    "fever", "bukhar", "pain", "abdomen", "chest", "cough", "cold", "weakness", "vomiting",
    "ulti", "dengue", "malaria", "typhoid", "diabetes", "hypertension", "asthma", "disease",
    "syndrome", "ward", "bed", "medicine", "surgery", "opd", "ipd", "emergency", "icu",
    "paracetamol", "ceftriaxone", "pantoprazole", "amoxicillin", "azithromycin", "metformin",
    "amlodipine", "atorvastatin", "dolo", "insulin", "ors", "tab", "inj", "cap", "syp",
    "tablet", "injection", "capsule", "syrup", "review", "diet", "normal", "positive",
    "negative", "report", "discharge", "summary", "final", "pending", "approved", "settled",
    "haemoglobin", "hemoglobin", "creatinine", "bilirubin", "platelet", "sugar", "blood",
    "pulse", "temp", "spo2", "weight", "male", "female", "patient", "attendant", "doctor",
    "hospital", "clinic", "pathology", "pharmacy", "billing", "claim", "helpdesk", "ticket",
    "worker", "workers", "nurse", "duty", "staff", "attendant", "multispeciality",
    "charitable", "sadan", "seva", "trust", "foundation", "laboratory", "center", "centre",
    "apollo", "department", "cardiology", "neurology", "oncology", "pediatrics", "orthopedics",
    "myocardial", "infarction", "lymphoma", "chronic", "kidney", "tuberculosis",
    "units", "twice", "thrice", "daily", "every", "hours", "hour", "hr", "hrs", "days", "weeks",
    "oral", "intravenous", "subcutaneous", "topical", "drops", "ointment", "cream", "inhaler",
    "bd", "tds", "qid", "od", "hs", "sos", "prn", "mg", "mcg", "ml", "mmol", "mmhg", "bpm", "kg", "cm", "dl",
}

_EPONYM_WORDS = {
    "addison", "addisons", "parkinson", "parkinsons", "crohn", "crohns", "hodgkin", "graves",
    "alzheimer", "alzheimers", "cushing", "bell", "guillain", "barre", "kawasaki", "meniere",
    "dyspnea", "micturition", "edema", "rash", "chills", "nausea", "headache", "jaundice",
    "बुखार", "दर्द", "खांसी", "उल्टी", "कमजोरी", "दस्त", "मलेरिया", "डेंगू", "टाइफाइड",
}
_EPONYM_SUFFIXES = {"disease", "syndrome", "lymphoma", "palsy", "triad", "sign"}

# ---------------------------------------------------------------------------
# Patterns for labeled names & relatives in free text (Multilingual)
# ---------------------------------------------------------------------------

RX_LABELED_NAME = re.compile(
    r"(?im)(?P<prefix>\b(?:Patient\s*Name|Pt\.?\s*Name|Patient|Pt\.|Beneficiary|Name|Report\s+of|"
    r"(?:Mareez|Rogi)(?:\s+ka\s+naam)?|नाम|मरीज|रोगी\s*का\s*नाम)\s*[:\-]\s*)"
    r"(?!Dr\.?\s)(?P<name>[A-Za-z\u0900-\u097f][A-Za-z\u0900-\u097f.\s]{1,45}?)"
    r"(?=\s*(?:\n|,|;|\||\.|आयु|Age|\d+\s*(?:Y|yrs|वर्ष)|$))"
)

RX_REPORT_OF = re.compile(
    r"(?im)(?P<prefix>\bReport\s+of\s+)(?!Dr\.?\s)(?P<name>[A-Za-z\u0900-\u097f][A-Za-z\u0900-\u097f.\s]{1,35}?)"
    r"(?=\s+(?:ji|sahab|saheb|behenji|bhaiya|bhai|didi|\d{1,3}\s*(?:Y|yrs|years|/)|[MF]\b|\n|$))"
)

RX_HONORIFIC_NAME = re.compile(
    r"(?m)(?<!Dr\.\s)(?<!Dr\s)\b(?P<name>(?:[A-Z][a-z]{2,18}|[\u0900-\u097f]{2,18})"
    r"(?:\s+(?:[A-Z][a-z]{2,18}|[\u0900-\u097f]{2,18}))?)"
    r"\s+(?P<hon>(?i:ji|sahab|saheb|behenji|bhaiya|bhaisahab|bhai|didi|bhabhiji|bhabhi|babu|papa|mummy|"
    r"amma|mataji|pitaji|chacha|chachu|chachi|mama|mamu|mami|tau|kaka|bua|mausi|fufa|dada|dadi|nana|nani|uncle|aunty)|जी|साहब|बाबू)\b"
)

# WhatsApp / chat sender: "[06/02/26, 7:56 pm] Raju Papa: ..."
RX_WHATSAPP_SENDER = re.compile(
    r"(?m)^(?P<prefix>\[\d{1,2}/\d{1,2}/\d{2,4},\s*\d{1,2}:\d{2}(?:\s*[ap]m)?\]\s*)(?P<name>[^:\n]{2,35}?)(?=:)"
)

# Contextual person roles (witness, caller, visitor/attendant)
RX_CONTEXT_PERSON = re.compile(
    r"(?m)(?P<prefix>(?i:\bwitnessed\s+by\s+|\bcalled\s+by\s+|\battendant\s*[:\-]\s*)|\b\d{1,2}:\d{2}\s*-\s*)"
    r"(?!Dr\.?\s)(?P<name>[A-Z][a-z]{1,18}(?:\s+[A-Z][a-z]{1,18}){1,2})(?=\s*(?:\(|,|;|\n|$|\d|(?i:C/O|S/O|D/O|W/O|H/O)\b))"
)

# Multilingual Relatives (S/o, D/o, W/o, H/o, Caregiver, Father, Mother, etc. in English & Hindi)
RX_RELATIVE = re.compile(
    r"(?m)(?P<rel>(?<!\w)(?:"
    r"S/O|D/O|W/O|H/O|S/o|D/o|W/o|H/o|s/o|d/o|w/o|h/o|"
    r"Father|Husband|Wife|Mother|Son|Daughter|Brother|Sister|Uncle|Aunt|Spouse|Cousin|Nephew|Niece|"
    r"brother|sister|uncle|aunt|spouse|cousin|nephew|niece|"
    r"Guardian|Caregiver|Attendant|Witness|"
    r"पिता|माता|पति|पत्नी|पुत्र|पुत्री|बेटा|बेटी|के\s+पुत्र|की\s+पत्नी|सपुत्र|वल्द|अभिभावक|परिचारक|गवाह|"
    r"(?i:pita\s+ka\s+naam|mata\s+ka\s+naam|pati\s+ka\s+naam|patni\s+ka\s+naam|pita|mata|pati|patni|beta|beti|walad)"
    r")(?:\s*[:\-]\s*|\s+(?:of\s+)?))"
    r"(?P<name>[A-Za-z\u0900-\u097f][A-Za-z\u0900-\u097f.\s]{1,35}?)(?=\s*(?:\n|,|;|\)|\.|who\b|which\b|signed\b|$))"
)

# C/O followed by person name (specifically guarding against "C/O fever", "C/O cough" etc.)
RX_CARE_OF_NAME = re.compile(
    r"(?m)(?P<rel>\b(?:C/O|c/o|Care\s+of)\s+)"
    r"(?!(?:fever|cough|cold|pain|vomiting|weakness|headache|chest\s+pain|diarrhea|rash|बुखार|खांसी|दर्द)\b)"
    r"(?P<name>[A-Z][a-z]{2,18}(?:\s+[A-Z][a-z]{2,18}){1,2}|[\u0900-\u097f]{2,18}(?:\s+[\u0900-\u097f]{2,18}){1,2})"
    r"(?=\s*(?:,|\n|$|\.))"
)

# Initial-based Indian names (e.g. "M. K. Sharma", "A. K. Gupta", "Mohd. Zenab")
RX_INITIAL_NAME = re.compile(
    r"\b(?:[A-Z]\.\s*){1,2}[A-Z][a-z]{2,18}\b"
)

# Doctor prefix guard & clinical organization/department guard
RX_DOCTOR = re.compile(r"\b(?:Dr\.?|Doctor|डॉक्टर|डॉ\.)\s+[A-Za-z\u0900-\u097f][A-Za-z\u0900-\u097f.]+(?:\s+[A-Za-z\u0900-\u097f][A-Za-z\u0900-\u097f]+){0,2}")
RX_ORG_PHRASE = re.compile(
    r"\b(?:(?:[A-Z][A-Za-z]+\s+){1,3}(?:Hospital|Medical\s+Center|Medical\s+Centre|Clinic|Institute|Nursing\s+Home)|"
    r"Department\s+of\s+[A-Z][A-Za-z]+(?:\s+[A-Z][A-Za-z]+){0,2})\b"
)


def is_clinical_phrase(text: str) -> bool:
    """Return True if text represents a clinical term, disease, or medical role."""
    toks = re.findall(r"[a-z\u0900-\u097f]+", text.casefold())
    if not toks:
        return False
    if "asha" in toks and (text.strip() == "ASHA" or "worker" in toks or "workers" in toks or "कार्यकर्ता" in toks):
        return True
    if any(t in CLINICAL_STOPWORDS for t in toks):
        return True
    if any(t in _EPONYM_WORDS for t in toks):
        # Treat eponym as clinical when single-word, possessive ('s), or paired with clinical suffix
        if len(toks) == 1 or "'" in text or any(t in _EPONYM_SUFFIXES for t in toks):
            return True
    return False


class CorpusNameIndex:
    """Dynamically learned index of patient & relative names from the input corpus.
    Maintains cross-script representations (Devanagari <-> Latin) and phonetic clusters.
    """

    def __init__(self) -> None:
        self.full_names: set[str] = set()
        self.first_names: set[str] = set()
        self.full_phonetic: set[str] = set()
        self._compiled_rx: re.Pattern[str] | None = None

    def add_name(self, raw_name: str) -> None:
        if not raw_name or len(raw_name.strip()) < 2:
            return
        cleaned = re.sub(r"\b(?:Dr\.?|Mr\.?|Mrs\.?|Ms\.?|Smt\.?|Shri\.?|डॉ\.?|श्री|श्रीमती)\s*", "", raw_name, flags=re.IGNORECASE).strip()
        cleaned = re.sub(r"\s+", " ", cleaned)
        if not cleaned or len(cleaned) < 3:
            return
        if cleaned.isupper() and len(cleaned) <= 6:
            return
        if is_clinical_phrase(cleaned):
            return

        self.full_names.add(cleaned)

        # Cross-script enrichment: if Devanagari, also add transliterated Latin name
        if is_devanagari(cleaned):
            latin_equiv = deva_to_latin(cleaned).title()
            if len(latin_equiv) >= 3:
                self.full_names.add(latin_equiv)
                parts_lat = latin_equiv.split()
                if parts_lat and len(parts_lat[0]) >= 3:
                    self.first_names.add(parts_lat[0])

        parts = cleaned.split()
        if len(parts) >= 1 and len(parts[0]) >= 3 and parts[0].casefold() not in CLINICAL_STOPWORDS and not parts[0].isupper():
            self.first_names.add(parts[0])

        ptoks = normalize_name_tokens(cleaned)
        if ptoks:
            self.full_phonetic.add(" ".join(ptoks))

        self._compiled_rx = None

    def build_matcher(self) -> re.Pattern[str] | None:
        if self._compiled_rx is not None:
            return self._compiled_rx
        # Sort longest first so full names match before single tokens
        candidates = sorted(self.full_names, key=len, reverse=True)
        escaped = [re.escape(c) for c in candidates if len(c) >= 3]
        if not escaped:
            return None
        # Match whole-word boundaries for Latin/Devanagari while never matching all-caps ASHA acronym
        pattern = r"(?<!\w)(?!(?-i:ASHA)\b)(?:" + "|".join(escaped) + r")(?!\w)"
        self._compiled_rx = re.compile(pattern, re.IGNORECASE)
        return self._compiled_rx


def extract_names_from_text(text: str, index: CorpusNameIndex) -> None:
    """Harvest high-confidence person names from free text into CorpusNameIndex."""
    for rx in (RX_LABELED_NAME, RX_REPORT_OF, RX_RELATIVE, RX_CARE_OF_NAME, RX_WHATSAPP_SENDER, RX_CONTEXT_PERSON):
        for m in rx.finditer(text):
            name = m.group("name").strip(" .,:;")
            if not is_clinical_phrase(name):
                index.add_name(name)
    for m in RX_HONORIFIC_NAME.finditer(text):
        name = m.group("name").strip(" .,:;")
        if not is_clinical_phrase(name):
            index.add_name(name)


_INDIAN_GIVEN_NAMES = frozenset({
    "aarav", "vivaan", "aditya", "vihaan", "arjun", "reyansh", "krishna", "ananya", "diya",
    "saanvi", "aadhya", "kavita", "sunita", "meera", "priya", "farhan", "zoya", "harpreet",
    "gurpreet", "rohan", "nikhil", "sneha", "pooja", "ramesh", "suresh", "lakshmi", "deepak",
    "meenakshi", "rajesh", "anita", "geeta", "reena", "salma", "usha", "parvati", "shahid",
    "fatima", "sunil", "tariq", "arvind", "rajeshwar", "harjinder", "sunanda", "rekha", "asha",
    "vikram", "amit", "sumit", "neha", "nisha", "rahul", "sanjay", "manoj", "prakash", "mahesh",
})
_INDIAN_SURNAMES = frozenset({
    "sharma", "verma", "deshmukh", "kulkarni", "subramanian", "sundaram", "nair", "iyer",
    "iyengar", "patel", "siddiqui", "khan", "kaur", "gill", "chatterjee", "banerjee",
    "mukherjee", "ganguly", "reddy", "rao", "mishra", "tiwari", "joshi", "gupta", "agarwal",
    "bansal", "singh", "kumar", "devi", "bano", "nishad", "chauhan", "ansari", "pandey",
    "yadav", "patil", "shinde", "jadhav", "bhat", "hegde", "menon", "pillai", "das",
})


def redact_names_in_text(
    text: str,
    index: CorpusNameIndex,
    local_first_names: set[str] | None = None,
) -> tuple[str, int]:
    """Redact labeled names, honorific names, relatives, and corpus-known names
    while strictly preserving Doctor names and clinical phrases.
    """
    if len(text) < 3 or not any(c.isalpha() for c in text):
        return text, 0
    count = 0
    # 1. Protect "Dr. <Name>" and clinical organization/department spans with temporary placeholders
    doc_spans: list[str] = []

    def _save_doc(m: re.Match[str]) -> str:
        doc_spans.append(m.group(0))
        return f"__RAKSHA_DOC_{len(doc_spans) - 1}__"

    work = RX_DOCTOR.sub(_save_doc, text) if ("dr" in text.casefold() or "डॉ" in text) else text
    work = RX_ORG_PHRASE.sub(_save_doc, work)

    # 1. Relatives: S/o, D/o, W/o, H/o, पिता, माता, पति, पत्नी, etc.
    def _sub_rel(m: re.Match[str]) -> str:
        nonlocal count
        name = m.group("name").strip()
        if is_clinical_phrase(name):
            return m.group(0)
        count += 1
        return f"{m.group('rel')}[RELATIVE_NAME]"

    work = RX_RELATIVE.sub(_sub_rel, work)
    work = RX_CARE_OF_NAME.sub(_sub_rel, work)

    # 2. Labeled patient names (Name:, नाम:, Report of ...)
    def _sub_labeled(m: re.Match[str]) -> str:
        nonlocal count
        name = m.group("name").strip()
        if is_clinical_phrase(name):
            return m.group(0)
        count += 1
        return f"{m.group('prefix')}[PATIENT_NAME]"

    work = RX_LABELED_NAME.sub(_sub_labeled, work)
    work = RX_REPORT_OF.sub(_sub_labeled, work)
    work = RX_WHATSAPP_SENDER.sub(_sub_labeled, work)
    work = RX_CONTEXT_PERSON.sub(_sub_labeled, work)

    # 3. Honorifics: "<Name> ji/sahab/behenji/didi/bhaiya/bhai/papa"
    def _sub_hon(m: re.Match[str]) -> str:
        nonlocal count
        name = m.group("name").strip()
        if is_clinical_phrase(name):
            return m.group(0)
        count += 1
        return f"[PATIENT_NAME] {m.group('hon')}"

    work = RX_HONORIFIC_NAME.sub(_sub_hon, work)

    # 4. Corpus-known full names (including cross-script transliterations)
    rx = index.build_matcher()
    if rx is not None:
        work, n = rx.subn("[PATIENT_NAME]", work)
        count += n

    # 5. Phonetic 2-word / 3-word name variants of corpus-known names
    if index.full_phonetic:
        def _sub_phonetic(m: re.Match[str]) -> str:
            nonlocal count
            cand = m.group(0)
            if is_clinical_phrase(cand):
                return cand
            ptoks = normalize_name_tokens(cand)
            if len(ptoks) >= 2 and " ".join(ptoks) in index.full_phonetic:
                count += 1
                return "[PATIENT_NAME]"
            return cand

        work = re.sub(r"\b[A-Z][a-z]{2,18}(?:\s+[A-Z][a-z]{2,18}){1,2}\b", _sub_phonetic, work)

    # 5b. Unlabeled Indian full names (gazetteer-anchored, strictly guarded by clinical/doctor/org protection)
    def _sub_unlabeled_indian(m: re.Match[str]) -> str:
        nonlocal count
        cand = m.group(0)
        if is_clinical_phrase(cand):
            return cand
        toks = [t.casefold() for t in cand.split()]
        if len(toks) >= 2 and (toks[0] in _INDIAN_GIVEN_NAMES or toks[-1] in _INDIAN_SURNAMES):
            if not any(t in CLINICAL_STOPWORDS for t in toks):
                count += 1
                return "[PATIENT_NAME]"
        return cand

    work = re.sub(r"\b[A-Z][a-z]{2,18}\s+[A-Z][a-z]{2,18}\b", _sub_unlabeled_indian, work)

    # 6. Record/file-local first names
    if local_first_names:
        safe_firsts = sorted(
            (fn for fn in local_first_names if len(fn) >= 3 and fn.casefold() not in CLINICAL_STOPWORDS and not fn.isupper()),
            key=len,
            reverse=True,
        )
        if safe_firsts:
            fn_rx = re.compile(
                r"(?<!\w)(?!(?-i:ASHA)\b)(?:" + "|".join(re.escape(f) for f in safe_firsts) + r")(?:'s)?(?!\w)",
                re.IGNORECASE,
            )
            work, n_fn = fn_rx.subn("[PATIENT_NAME]", work)
            count += n_fn

    # 7. Restore protected "Dr. <Name>" spans
    for i, doc_str in enumerate(doc_spans):
        work = work.replace(f"__RAKSHA_DOC_{i}__", doc_str)

    return work, count
