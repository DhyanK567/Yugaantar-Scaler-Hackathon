"""Multilingual (English, Hindi/Devanagari, Hinglish) name, relative & transliteration engine
with strict medical-context preservation guards.
"""
from __future__ import annotations

import re
import unicodedata

# ---------------------------------------------------------------------------
# Devanagari -> Latin phonetic transliteration (rule-based, zero dependencies)
# ---------------------------------------------------------------------------
_CONSONANTS = {
    "क": "k", "ख": "kh", "ग": "g", "घ": "gh", "ङ": "ng",
    "च": "ch", "छ": "chh", "ज": "j", "झ": "jh", "ञ": "ny",
    "ट": "t", "ठ": "th", "ड": "d", "ढ": "dh", "ण": "n",
    "त": "t", "थ": "th", "द": "d", "ध": "dh", "न": "n",
    "प": "p", "फ": "ph", "ब": "b", "भ": "bh", "म": "m",
    "य": "y", "र": "r", "ल": "l", "व": "v", "श": "sh",
    "ष": "sh", "स": "s", "ह": "h",
    "क़": "q", "ख़": "kh", "ग़": "gh", "ज़": "z", "ड़": "r", "ढ़": "rh", "फ़": "f",
}
_VOWELS_INDEP = {
    "अ": "a", "आ": "aa", "इ": "i", "ई": "ee", "उ": "u", "ऊ": "oo",
    "ऋ": "ri", "ए": "e", "ऐ": "ai", "ओ": "o", "औ": "au",
    "अं": "an", "अः": "ah",
}
_MATRAS = {
    "ा": "a", "ि": "i", "ी": "ee", "ु": "u", "ू": "oo",
    "ृ": "ri", "े": "e", "ै": "ai", "ो": "o", "ौ": "au",
    "ं": "n", "ँ": "n", "ः": "h", "्": "",
}
_VIRAMA = "्"


def deva_to_latin(text: str) -> str:
    """Transliterate Devanagari text to approximate Latin phonetic form."""
    out: list[str] = []
    n = len(text)
    i = 0
    while i < n:
        ch = text[i]
        # Handle nukta combinations (base + ़)
        if i + 1 < n and text[i + 1] == "़" and (ch + "़") in _CONSONANTS:
            ch = ch + "़"
            i += 1
        if ch in _CONSONANTS:
            out.append(_CONSONANTS[ch])
            nxt = text[i + 1] if i + 1 < n else ""
            if nxt in _MATRAS:
                if nxt != _VIRAMA:
                    out.append(_MATRAS[nxt])
                i += 1
            elif nxt and nxt in _CONSONANTS:
                # Inherent schwa 'a' between consonants
                out.append("a")
        elif ch in _VOWELS_INDEP:
            out.append(_VOWELS_INDEP[ch])
        elif ch in _MATRAS:
            out.append(_MATRAS[ch])
        else:
            out.append(ch)
        i += 1
    return "".join(out)


# Common Indian name abbreviation / spelling equivalences
_PHONETIC_SUBS = [
    (re.compile(r"\b(?:mohd|md|mohammad|muhammad|mohammed|mohamed)\b"), "mohammad"),
    (re.compile(r"\b(?:smt|shrimati|mrs|ms|kumari|km|shri|mr)\b\.?"), ""),
    (re.compile(r"aa+"), "a"),
    (re.compile(r"ee+"), "i"),
    (re.compile(r"oo+"), "u"),
    (re.compile(r"ai"), "e"),
    (re.compile(r"ph"), "f"),
    (re.compile(r"v"), "w"),
    (re.compile(r"sh"), "s"),
    (re.compile(r"z"), "j"),
    (re.compile(r"q"), "k"),
    (re.compile(r"(.)\1+"), r"\1"),
]


def phonetic_norm(token: str) -> str:
    """Normalize a Latin or Devanagari name token to a phonetic skeleton."""
    t = unicodedata.normalize("NFKC", token).casefold().strip()
    if any("\u0900" <= c <= "\u097f" for c in t):
        t = deva_to_latin(t)
    t = re.sub(r"[^a-z]", "", t)
    if not t:
        return ""
    for rx, rep in _PHONETIC_SUBS:
        t = rx.sub(rep, t)
    return t


def normalize_name_tokens(name: str) -> list[str]:
    """Return normalized phonetic tokens for a person name (excluding honorifics)."""
    s = unicodedata.normalize("NFKC", name).casefold()
    if any("\u0900" <= c <= "\u097f" for c in s):
        s = deva_to_latin(s)
    # Expand common abbreviations before stripping punctuation
    s = re.sub(r"\b(?:mohd|md)\.?\b", "mohammad", s)
    s = re.sub(r"\b(?:smt|shri|dr|mr|mrs|ms|km)\.?\b", " ", s)
    raw_tokens = re.findall(r"[a-z]+", s)
    stop = {"ji", "sahab", "saheb", "behenji", "bhaiya", "didi", "bhai", "devi", "kumar", "kumari", "lal", "singh", "kaur"}
    out = []
    for tok in raw_tokens:
        if tok in {"ji", "sahab", "saheb", "behenji", "bhaiya", "didi", "bhai"}:
            continue
        p = phonetic_norm(tok)
        if len(p) >= 2:
            out.append(p)
    # If all tokens were generic (e.g., "Devi"), keep them as fallback
    if not out:
        out = [phonetic_norm(t) for t in raw_tokens if len(t) >= 2]
    return out


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
    "addison", "addisons", "parkinson", "parkinsons", "crohn", "crohns", "hodgkin", "graves",
    "alzheimer", "alzheimers", "cushing", "bell", "guillain", "barre", "kawasaki", "meniere",
}

# Patterns for labeled names & relatives in free text
RX_LABELED_NAME = re.compile(
    r"(?im)(?P<prefix>\b(?:Patient\s*Name|Pt\.?\s*Name|Patient|Pt\.|Beneficiary|Name|Report\s+of|नाम|मरीज)\s*[:\-]\s*)"
    r"(?!Dr\.?\s)(?P<name>[A-Za-z\u0900-\u097f][A-Za-z\u0900-\u097f.\s]{1,45}?)(?=\s*(?:\n|,|;|\||आयु|Age|\d+\s*(?:Y|yrs|वर्ष)|$))"
)

RX_REPORT_OF = re.compile(
    r"(?im)(?P<prefix>\bReport\s+of\s+)(?!Dr\.?\s)(?P<name>[A-Za-z\u0900-\u097f][A-Za-z\u0900-\u097f.\s]{1,35}?)"
    r"(?=\s+(?:ji|sahab|saheb|behenji|bhaiya|bhai|didi|\d{1,3}\s*(?:Y|yrs|years|/)|[MF]\b|\n|$))"
)

RX_HONORIFIC_NAME = re.compile(
    r"(?m)(?<!Dr\.\s)(?<!Dr\s)\b(?P<name>(?:[A-Z][a-z]{2,18}|[\u0900-\u097f]{2,18})(?:\s+(?:[A-Z][a-z]{2,18}|[\u0900-\u097f]{2,18}))?)"
    r"\s+(?P<hon>(?i:ji|sahab|saheb|behenji|bhaiya|bhaisahab|bhai|didi|bhabhiji|bhabhi|papa|mummy|amma|mataji|pitaji|chacha|chachu|chachi|mama|mamu|mami|tau|kaka|bua|mausi|fufa|dada|dadi|nana|nani|uncle|aunty)|जी|साहब)\b"
)

# WhatsApp / chat sender: "[06/02/26, 7:56 pm] Raju Papa: ..."
RX_WHATSAPP_SENDER = re.compile(
    r"(?m)^(?P<prefix>\[\d{1,2}/\d{1,2}/\d{2,4},\s*\d{1,2}:\d{2}(?:\s*[ap]m)?\]\s*)(?P<name>[^:\n]{2,35}?)(?=:)"
)

# Contextual person roles (witness, caller, visitor/attendant)
RX_CONTEXT_PERSON = re.compile(
    r"(?m)(?P<prefix>(?i:\bwitnessed\s+by\s+|\bcalled\s+by\s+|\battendant\s*[:\-]\s*)|\b\d{1,2}:\d{2}\s*-\s*)"
    r"(?!Dr\.?\s)(?P<name>[A-Z][a-z]{1,18}(?:\s+[A-Z][a-z]{1,18}){1,2})(?=\s*(?:\(|,|;|\n|$|\d))"
)

# Relatives: S/o, D/o, W/o, and C/O ONLY when followed by capitalized/Devanagari name (not C/O fever/pain!)
RX_RELATIVE = re.compile(
    r"(?m)(?P<rel>\b(?:S/o|D/o|W/o|s/o|d/o|w/o|Father|Husband|Wife|Mother)\s*[:\-]?\s*)"
    r"(?P<name>[A-Za-z\u0900-\u097f][A-Za-z\u0900-\u097f.\s]{1,35}?)(?=\s*(?:\n|,|;|\)|$))"
)
RX_CARE_OF_NAME = re.compile(
    r"(?m)(?P<rel>\bC/O\s+)(?P<name>[A-Z][a-z]{2,18}(?:\s+[A-Z][a-z]{2,18}){1,2})(?=\s*(?:,|\n|$))"
)

# Doctor prefix guard: matches "Dr. Ramesh Srivastava" or "Dr Ramesh"
RX_DOCTOR = re.compile(r"\bDr\.?\s+[A-Z][a-zA-Z.]+(?:\s+[A-Z][a-zA-Z]+){0,2}")


def is_clinical_phrase(text: str) -> bool:
    toks = re.findall(r"[a-z]+", text.casefold())
    if not toks:
        return False
    if "asha" in toks and (text.strip() == "ASHA" or "worker" in toks or "workers" in toks):
        return True
    return any(t in CLINICAL_STOPWORDS for t in toks)


class CorpusNameIndex:
    """Dynamically learned index of patient & relative names from the input corpus."""

    def __init__(self) -> None:
        self.full_names: set[str] = set()
        self.first_names: set[str] = set()
        self.full_phonetic: set[str] = set()
        self._compiled_rx: re.Pattern[str] | None = None

    def add_name(self, raw_name: str) -> None:
        if not raw_name or len(raw_name.strip()) < 2:
            return
        cleaned = re.sub(r"\b(?:Dr\.?|Mr\.?|Mrs\.?|Ms\.?|Smt\.?|Shri\.?)\s*", "", raw_name, flags=re.IGNORECASE).strip()
        cleaned = re.sub(r"\s+", " ", cleaned)
        if not cleaned or len(cleaned) < 3:
            return
        if cleaned.isupper() and len(cleaned) <= 6:
            return
        if is_clinical_phrase(cleaned):
            return
        self.full_names.add(cleaned)
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
        escaped = [re.escape(c) for c in candidates if len(c) >= 4]
        if not escaped:
            return None
        # Match whole-word boundaries (works for Latin; for Devanagari, \b or whitespace/punct)
        pattern = r"(?<!\w)(?:" + "|".join(escaped) + r")(?!\w)"
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


def redact_names_in_text(
    text: str,
    index: CorpusNameIndex,
    local_first_names: set[str] | None = None,
) -> tuple[str, int]:
    """Redact labeled names, honorific names, relatives, and corpus-known names
    while strictly preserving Doctor names and clinical phrases.
    """
    count = 0
    # 1. Protect "Dr. <Name>" spans with temporary placeholders
    doc_spans: list[str] = []

    def _save_doc(m: re.Match[str]) -> str:
        doc_spans.append(m.group(0))
        return f"__RAKSHA_DOC_{len(doc_spans) - 1}__"

    work = RX_DOCTOR.sub(_save_doc, text)

    # 2. Relatives: S/o, D/o, W/o, C/O <Name>
    def _sub_rel(m: re.Match[str]) -> str:
        nonlocal count
        name = m.group("name").strip()
        if is_clinical_phrase(name):
            return m.group(0)
        count += 1
        return f"{m.group('rel')}[RELATIVE_NAME]"

    work = RX_RELATIVE.sub(_sub_rel, work)
    work = RX_CARE_OF_NAME.sub(_sub_rel, work)

    # 3. Labeled patient names (Name:, नाम:, Report of ...)
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

    # 4. Honorifics: "<Name> ji/sahab/behenji/didi/bhaiya/bhai/papa"
    def _sub_hon(m: re.Match[str]) -> str:
        nonlocal count
        name = m.group("name").strip()
        if is_clinical_phrase(name):
            return m.group(0)
        count += 1
        return f"[PATIENT_NAME] {m.group('hon')}"

    work = RX_HONORIFIC_NAME.sub(_sub_hon, work)

    # 5. Corpus-known full names (catches unlabeled mentions in Hindi/English/Hinglish)
    rx = index.build_matcher()
    if rx is not None:
        work, n = rx.subn("[PATIENT_NAME]", work)
        count += n

    # 5b. Phonetic 2-word name variants of corpus-known names (e.g., Zenab Bano <-> Zainab Bano)
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

        work = re.sub(r"\b[A-Z][a-z]{2,18}\s+[A-Z][a-z]{2,18}\b", _sub_phonetic, work)

    # 6. Record/file-local first names (catches "Rajan's attendant", "Irfan ka BP", CSV headers)
    if local_first_names:
        safe_firsts = sorted(
            (fn for fn in local_first_names if len(fn) >= 3 and fn.casefold() not in CLINICAL_STOPWORDS and not fn.isupper()),
            key=len,
            reverse=True,
        )
        if safe_firsts:
            fn_rx = re.compile(r"(?<!\w)(?!ASHA\b)(?:" + "|".join(re.escape(f) for f in safe_firsts) + r")(?:'s)?(?!\w)")
            work, n_fn = fn_rx.subn("[PATIENT_NAME]", work)
            count += n_fn

    # 7. Restore protected "Dr. <Name>" spans
    for i, doc_str in enumerate(doc_spans):
        work = work.replace(f"__RAKSHA_DOC_{i}__", doc_str)

    return work, count
