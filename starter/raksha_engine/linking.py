"""Conservative cross-file patient identity resolution.

Links records across CSV, JSON, FHIR, and free-text files using strong IDs
(PHONE, AADHAAR, ABHA, PAN, MRN/UHID) and supporting clues (transliterated
name tokens, DOB/age, gender, village/district), while strictly preventing
false merges on homonyms or insufficient evidence.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field

from .names import normalize_name_tokens
from .patterns import (
    RX_AADHAAR,
    RX_ABHA_NUM,
    RX_DOB_LABEL,
    RX_EMAIL,
    RX_MRN,
    RX_PAN,
    RX_PHONE,
    RX_PIN,
    normalize_digits,
)


@dataclass
class RecordClues:
    record_id: str  # unique deterministic key, e.g. f"{rel}::{loc}"
    strong_ids: set[str] = field(default_factory=set)  # phone:..., aadhaar:..., abha:..., pan:..., email:...
    mrns: set[str] = field(default_factory=set)  # mrn:...
    name_tokens: list[str] = field(default_factory=list)
    full_phonetic_name: str = ""
    gender: str = ""  # M / F / O
    birth_year: int | None = None
    age: int | None = None
    pin: str = ""
    district: str = ""
    village: str = ""

    def has_strong_identity(self) -> bool:
        return bool(self.strong_ids or self.mrns or (len(self.name_tokens) >= 2 and (self.birth_year or self.age or self.district or self.village)))


def _norm_mrn(val: str) -> str:
    return re.sub(r"[^A-Z0-9]", "", val.upper())


def _norm_phone(val: str) -> str:
    d = re.sub(r"\D", "", normalize_digits(val))
    if len(d) >= 10:
        return d[-10:]
    return ""


def _norm_gender(val: str) -> str:
    v = val.strip().upper()
    if v in ("M", "MALE", "पुरुष"):
        return "M"
    if v in ("F", "FEMALE", "महिला"):
        return "F"
    if v in ("O", "OTHER"):
        return "O"
    return ""


def extract_clues_from_text(record_id: str, text: str) -> RecordClues:
    """Extract identity clues from unstructured text."""
    clues = RecordClues(record_id=record_id)
    t = normalize_digits(text)

    for m in RX_ABHA_NUM.finditer(t):
        d = re.sub(r"\D", "", m.group(0))
        if len(d) == 14:
            clues.strong_ids.add(f"abha:{d}")
    for m in RX_AADHAAR.finditer(t):
        d = re.sub(r"\D", "", m.group(0))
        if len(d) == 12:
            clues.strong_ids.add(f"aadhaar:{d}")
    for m in RX_PHONE.finditer(t):
        p = _norm_phone(m.group(0))
        if p:
            clues.strong_ids.add(f"phone:{p}")
    for m in RX_EMAIL.finditer(t):
        clues.strong_ids.add(f"email:{m.group(0).casefold()}")
    for m in RX_PAN.finditer(t):
        clues.strong_ids.add(f"pan:{m.group(0).upper()}")
    for m in RX_MRN.finditer(t):
        clues.mrns.add(f"mrn:{_norm_mrn(m.group(0))}")
    for m in RX_PIN.finditer(t):
        clues.pin = m.group(0)
        break

    # Age / Gender in text like "48 Y / F" or "आयु: 39 वर्ष"
    m_ag = re.search(r"\b(\d{1,3})\s*(?:Y|yrs|years)?\s*/\s*([MF])\b", t, re.IGNORECASE)
    if m_ag:
        clues.age = int(m_ag.group(1))
        clues.gender = m_ag.group(2).upper()
    else:
        m_age = re.search(r"(?:Age|आयु|उम्र)\s*[:\-]?\s*(\d{1,3})", t, re.IGNORECASE)
        if m_age:
            clues.age = int(m_age.group(1))

    m_dob = RX_DOB_LABEL.search(t)
    if m_dob:
        ym = re.search(r"(19\d{2}|20\d{2})", m_dob.group(1))
        if ym:
            clues.birth_year = int(ym.group(1))

    return clues


def merge_clues(base: RecordClues, extra: RecordClues) -> None:
    base.strong_ids.update(extra.strong_ids)
    base.mrns.update(extra.mrns)
    if not base.name_tokens and extra.name_tokens:
        base.name_tokens = extra.name_tokens
        base.full_phonetic_name = extra.full_phonetic_name
    if not base.gender and extra.gender:
        base.gender = extra.gender
    if not base.birth_year and extra.birth_year:
        base.birth_year = extra.birth_year
    if not base.age and extra.age:
        base.age = extra.age
    if not base.pin and extra.pin:
        base.pin = extra.pin
    if not base.district and extra.district:
        base.district = extra.district
    if not base.village and extra.village:
        base.village = extra.village


def set_name_clue(clues: RecordClues, name: str) -> None:
    toks = normalize_name_tokens(name)
    if toks and not clues.name_tokens:
        clues.name_tokens = toks
        clues.full_phonetic_name = " ".join(toks)


def _compatible(a: RecordClues, b: RecordClues) -> bool:
    """Return False if two records have contradictory demographics (homonym guard)."""
    if a.gender and b.gender and a.gender != b.gender:
        return False
    if a.birth_year and b.birth_year and abs(a.birth_year - b.birth_year) > 1:
        return False
    if a.age is not None and b.age is not None and abs(a.age - b.age) > 3:
        return False
    # If both have full phonetic names with >=2 tokens and they completely disagree,
    # only allow merge if they share a globally unique strong ID (aadhaar/abha/pan)
    if a.full_phonetic_name and b.full_phonetic_name:
        if a.name_tokens[0] != b.name_tokens[0] and not (a.strong_ids & b.strong_ids):
            return False
    return True


def resolve_identities(all_clues: list[RecordClues]) -> dict[str, str | None]:
    """Cluster records conservatively and return {record_id: canonical_cluster_key | None}."""
    n = len(all_clues)
    parent = list(range(n))

    def find(x: int) -> int:
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    def union(i: int, j: int) -> None:
        ri, rj = find(i), find(j)
        if ri != rj:
            if ri < rj:
                parent[rj] = ri
            else:
                parent[ri] = rj

    # Build deterministic blocking indices
    by_strong: dict[str, list[int]] = {}
    by_mrn: dict[str, list[int]] = {}
    by_name: dict[str, list[int]] = {}

    for idx, c in enumerate(all_clues):
        for sid in sorted(c.strong_ids):
            by_strong.setdefault(sid, []).append(idx)
        for mrn in sorted(c.mrns):
            by_mrn.setdefault(mrn, []).append(idx)
        if c.full_phonetic_name and len(c.name_tokens) >= 2:
            by_name.setdefault(c.full_phonetic_name, []).append(idx)

    # 1. Link on unique strong IDs (Aadhaar, ABHA, PAN, Phone, Email)
    for sid, idxs in by_strong.items():
        if len(idxs) > 1:
            anchor = idxs[0]
            for other in idxs[1:]:
                if _compatible(all_clues[anchor], all_clues[other]):
                    union(anchor, other)

    # 2. Link on MRN / UHID
    for mrn, idxs in by_mrn.items():
        if len(idxs) > 1:
            anchor = idxs[0]
            for other in idxs[1:]:
                if _compatible(all_clues[anchor], all_clues[other]):
                    union(anchor, other)

    # 3. Link on exact phonetic full name ONLY when supported by >= 1 corroborating clue
    #    (birth_year, age within 2, pin, village, or district) and no contradiction
    for pname, idxs in by_name.items():
        if len(idxs) < 2:
            continue
        for i_pos in range(len(idxs)):
            i = idxs[i_pos]
            ci = all_clues[i]
            for j_pos in range(i_pos + 1, len(idxs)):
                j = idxs[j_pos]
                cj = all_clues[j]
                if not _compatible(ci, cj):
                    continue
                corroborations = 0
                if ci.birth_year and cj.birth_year and ci.birth_year == cj.birth_year:
                    corroborations += 2
                if ci.age is not None and cj.age is not None and abs(ci.age - cj.age) <= 2:
                    corroborations += 1
                if ci.pin and cj.pin and ci.pin == cj.pin:
                    corroborations += 1
                if ci.district and cj.district and ci.district.casefold() == cj.district.casefold():
                    corroborations += 1
                if ci.village and cj.village and ci.village.casefold() == cj.village.casefold():
                    corroborations += 2
                if corroborations >= 2:
                    union(i, j)

    # Group into clusters and assign canonical cluster keys
    clusters: dict[int, list[int]] = {}
    for idx in range(n):
        clusters.setdefault(find(idx), []).append(idx)

    result: dict[str, str | None] = {}
    for root, members in clusters.items():
        # Only assign a pseudonym if at least one member has a strong identity
        if len(members) == 1 and not all_clues[members[0]].has_strong_identity():
            result[all_clues[members[0]].record_id] = None
            continue
        # Canonical deterministic key: sorted record_ids / strong_ids
        sids = sorted({s for m in members for s in (all_clues[m].strong_ids | all_clues[m].mrns)})
        if sids:
            ckey = "cluster|" + "|".join(sids[:3])
        else:
            ckey = "cluster|" + "|".join(sorted(all_clues[m].record_id for m in members)[:2])
        for m in members:
            result[all_clues[m].record_id] = ckey

    return result
