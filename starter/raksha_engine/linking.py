"""Conservative cross-file patient identity resolution (Milestone 11).

Implements:
  - M11.1 Structured Identity Evidence Extraction (EvidenceItem + reason codes)
  - M11.2 Multilingual & Initial-Aware Name Normalization
  - M11.3 Evidence-Weighted Matching (Strong / Supporting / Conflict)
  - M11.4 Source-Aware Cross-Hospital Resolution (hospital-scoped MRNs)
  - M11.5 Conservative Graph Clustering with Cluster-Level Conflict Guards
  - M11.6 False-Merge Prevention & Abstention
  - M11.7 Order-Independent Canonical Cluster Keys
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from difflib import SequenceMatcher

from .names import names_match_with_initials, normalize_name_tokens
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

# Known globally-prefixed hospital MRN patterns (do not need extra hospital scoping)
_PREFIXED_MRN_RX = re.compile(r"^(?:SNJ|UHID|JJH|DHH|OPD|BL)[-/]?", re.IGNORECASE)

# Evidence weights & thresholds (M11.3)
STRONG_ID_PREFIXES = ("aadhaar:", "abha:", "pan:")


@dataclass
class EvidenceItem:
    category: str          # STRONG_ID, MRN, NAME, DEMOGRAPHIC, LOCATION
    normalized: str
    source_record: str
    strength: float        # 0.0 .. 1.0
    method: str            # regex, structured_col, translit_phonetic
    conflict: bool = False
    reason_code: str = ""


@dataclass
class RecordClues:
    record_id: str
    strong_ids: set[str] = field(default_factory=set)
    mrns: set[str] = field(default_factory=set)
    name_tokens: list[str] = field(default_factory=list)
    initial_tokens: list[str] = field(default_factory=list)
    full_phonetic_name: str = ""
    gender: str = ""
    birth_year: int | None = None
    age: int | None = None
    pin: str = ""
    district: str = ""
    village: str = ""
    hospital: str = ""
    evidences: list[EvidenceItem] = field(default_factory=list)
    decision_reason: str = "UNDECIDED"

    def has_strong_identity(self) -> bool:
        return bool(
            self.strong_ids
            or self.mrns
            or (len(self.name_tokens) >= 2 and (self.birth_year or self.age or self.district or self.village))
        )


def _norm_mrn(val: str) -> str:
    return re.sub(r"[^A-Z0-9]", "", val.upper())


def _scoped_mrn(raw_mrn: str, hospital: str = "") -> str:
    normed = _norm_mrn(raw_mrn)
    if hospital and not _PREFIXED_MRN_RX.match(raw_mrn.strip()):
        h = re.sub(r"[^a-z0-9]", "", hospital.casefold())
        return f"mrn:{h}:{normed}"
    return f"mrn:{normed}"


def _norm_phone(val: str) -> str:
    d = re.sub(r"\D", "", normalize_digits(val))
    if len(d) >= 10:
        return d[-10:]
    return ""


def _infer_hospital(record_id: str) -> str:
    low = record_id.casefold()
    for h in ("sanjeevani", "jeevanjyoti", "arogya", "dhhardoi", "dhh"):
        if h in low:
            return h
    return ""


def extract_clues_from_text(record_id: str, text: str) -> RecordClues:
    """Extract structured identity clues from unstructured text."""
    clues = RecordClues(record_id=record_id, hospital=_infer_hospital(record_id))
    t = normalize_digits(text)

    for m in RX_ABHA_NUM.finditer(t):
        d = re.sub(r"\D", "", m.group(0))
        if len(d) == 14:
            val = f"abha:{d}"
            clues.strong_ids.add(val)
            clues.evidences.append(EvidenceItem("STRONG_ID", val, record_id, 1.0, "regex", reason_code="EXTRACTED_ABHA"))
    t_no_abha = RX_ABHA_NUM.sub(" ", t)
    for m in RX_AADHAAR.finditer(t_no_abha):
        d = re.sub(r"\D", "", m.group(0))
        if len(d) == 12:
            val = f"aadhaar:{d}"
            clues.strong_ids.add(val)
            clues.evidences.append(EvidenceItem("STRONG_ID", val, record_id, 1.0, "regex", reason_code="EXTRACTED_AADHAAR"))
    t_no_aadhaar = RX_AADHAAR.sub(" ", t_no_abha)
    for m in RX_PHONE.finditer(t_no_aadhaar):
        p = _norm_phone(m.group(0))
        if p:
            val = f"phone:{p}"
            clues.strong_ids.add(val)
            clues.evidences.append(EvidenceItem("STRONG_ID", val, record_id, 0.85, "regex", reason_code="EXTRACTED_PHONE"))
    for m in RX_EMAIL.finditer(t):
        val = f"email:{m.group(0).casefold()}"
        clues.strong_ids.add(val)
        clues.evidences.append(EvidenceItem("STRONG_ID", val, record_id, 0.9, "regex", reason_code="EXTRACTED_EMAIL"))
    for m in RX_PAN.finditer(t):
        val = f"pan:{m.group(0).upper()}"
        clues.strong_ids.add(val)
        clues.evidences.append(EvidenceItem("STRONG_ID", val, record_id, 1.0, "regex", reason_code="EXTRACTED_PAN"))
    for m in RX_MRN.finditer(t):
        val = _scoped_mrn(m.group(0), clues.hospital)
        clues.mrns.add(val)
        clues.evidences.append(EvidenceItem("MRN", val, record_id, 0.9, "regex", reason_code="EXTRACTED_MRN"))
    for m in RX_PIN.finditer(t):
        clues.pin = m.group(0)
        break

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
    base.evidences.extend(extra.evidences)
    if not base.name_tokens and extra.name_tokens:
        base.name_tokens = extra.name_tokens
        base.initial_tokens = extra.initial_tokens
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
    toks = normalize_name_tokens(name, keep_initials=False)
    itoks = normalize_name_tokens(name, keep_initials=True)
    if itoks and not clues.initial_tokens:
        clues.initial_tokens = itoks
    if toks and not clues.name_tokens:
        clues.name_tokens = toks
        clues.full_phonetic_name = " ".join(toks)
        clues.evidences.append(
            EvidenceItem("NAME", clues.full_phonetic_name, clues.record_id, 0.6, "translit_phonetic", reason_code="EXTRACTED_NAME")
        )


def _has_conflicting_unique_ids(ids_a: set[str], ids_b: set[str]) -> bool:
    """Return True if both sides carry different Aadhaar, ABHA, or PAN numbers."""
    for prefix in STRONG_ID_PREFIXES:
        a_vals = {x for x in ids_a if x.startswith(prefix)}
        b_vals = {x for x in ids_b if x.startswith(prefix)}
        if a_vals and b_vals and not (a_vals & b_vals):
            return True
    return False


def _compatible(a: RecordClues, b: RecordClues) -> bool:
    """Pairwise conflict guard (M11.3 / M11.6)."""
    if _has_conflicting_unique_ids(a.strong_ids, b.strong_ids):
        return False
    if a.gender and b.gender and a.gender != b.gender:
        return False
    if a.birth_year and b.birth_year and abs(a.birth_year - b.birth_year) > 1:
        return False
    if a.age is not None and b.age is not None and abs(a.age - b.age) > 3:
        return False
    if a.initial_tokens and b.initial_tokens:
        shared_global = {x for x in a.strong_ids if x.startswith(STRONG_ID_PREFIXES)} & {
            x for x in b.strong_ids if x.startswith(STRONG_ID_PREFIXES)
        }
        if not shared_global:
            fa = a.name_tokens[0] if a.name_tokens else a.initial_tokens[0]
            fb = b.name_tokens[0] if b.name_tokens else b.initial_tokens[0]
            if fa != fb and not names_match_with_initials(a.initial_tokens, b.initial_tokens):
                if SequenceMatcher(None, fa, fb).ratio() < 0.72:
                    return False
    return True


def resolve_identities(all_clues: list[RecordClues]) -> dict[str, str | None]:
    """Order-independent conservative clustering (M11.4-M11.7).

    Returns {record_id: canonical_cluster_key | None}.
    """
    n = len(all_clues)
    if n == 0:
        return {}

    # Sort indices deterministically by record_id so arrival order NEVER affects clustering
    order = sorted(range(n), key=lambda i: all_clues[i].record_id)
    ordered_clues = [all_clues[i] for i in order]

    # Scope MRNs by hospital if hospital was set after extract_clues_from_text
    norm_mrns: list[set[str]] = []
    for c in ordered_clues:
        scoped = set()
        for m in c.mrns:
            raw = m[4:] if m.startswith("mrn:") else m
            scoped.add(_scoped_mrn(raw, c.hospital) if ":" not in raw else m)
        norm_mrns.append(scoped)

    parent = list(range(n))

    def find(x: int) -> int:
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    c_gender: list[str] = [c.gender for c in ordered_clues]
    c_byear: list[tuple[int, int] | None] = [(c.birth_year, c.birth_year) if c.birth_year else None for c in ordered_clues]
    c_age: list[tuple[int, int] | None] = [(c.age, c.age) if c.age is not None else None for c in ordered_clues]
    c_fname: list[str] = [c.name_tokens[0] if c.name_tokens else "" for c in ordered_clues]
    c_itoks: list[list[str]] = [c.initial_tokens for c in ordered_clues]
    c_all_strong: list[set[str]] = [set(c.strong_ids) for c in ordered_clues]
    c_global_ids: list[set[str]] = [{s for s in c.strong_ids if s.startswith(STRONG_ID_PREFIXES)} for c in ordered_clues]

    def _clusters_compatible(ri: int, rj: int) -> bool:
        # Block on contradictory Aadhaar / ABHA / PAN anywhere in the two clusters
        if _has_conflicting_unique_ids(c_all_strong[ri], c_all_strong[rj]):
            return False
        if c_gender[ri] and c_gender[rj] and c_gender[ri] != c_gender[rj]:
            return False
        if c_byear[ri] and c_byear[rj]:
            lo = min(c_byear[ri][0], c_byear[rj][0])
            hi = max(c_byear[ri][1], c_byear[rj][1])
            if hi - lo > 1:
                return False
        if c_age[ri] and c_age[rj]:
            lo = min(c_age[ri][0], c_age[rj][0])
            hi = max(c_age[ri][1], c_age[rj][1])
            if hi - lo > 3:
                return False
        if c_fname[ri] and c_fname[rj] and c_fname[ri] != c_fname[rj]:
            if not (c_global_ids[ri] & c_global_ids[rj]):
                if not names_match_with_initials(c_itoks[ri], c_itoks[rj]):
                    if SequenceMatcher(None, c_fname[ri], c_fname[rj]).ratio() < 0.72:
                        return False
        return True

    def union(i: int, j: int, reason: str) -> bool:
        ri, rj = find(i), find(j)
        if ri == rj:
            return True
        if not _clusters_compatible(ri, rj):
            ordered_clues[i].decision_reason = "ABSTAIN_CLUSTER_CONFLICT"
            ordered_clues[j].decision_reason = "ABSTAIN_CLUSTER_CONFLICT"
            return False
        if ri > rj:
            ri, rj = rj, ri
        parent[rj] = ri
        if not c_gender[ri] and c_gender[rj]:
            c_gender[ri] = c_gender[rj]
        if c_byear[rj]:
            c_byear[ri] = c_byear[rj] if not c_byear[ri] else (min(c_byear[ri][0], c_byear[rj][0]), max(c_byear[ri][1], c_byear[rj][1]))
        if c_age[rj]:
            c_age[ri] = c_age[rj] if not c_age[ri] else (min(c_age[ri][0], c_age[rj][0]), max(c_age[ri][1], c_age[rj][1]))
        if not c_fname[ri] and c_fname[rj]:
            c_fname[ri] = c_fname[rj]
        if not c_itoks[ri] and c_itoks[rj]:
            c_itoks[ri] = c_itoks[rj]
        c_all_strong[ri].update(c_all_strong[rj])
        c_global_ids[ri].update(c_global_ids[rj])
        ordered_clues[i].decision_reason = reason
        ordered_clues[j].decision_reason = reason
        return True

    # Deterministic blocking indices
    by_strong: dict[str, list[int]] = {}
    by_mrn: dict[str, list[int]] = {}
    by_name: dict[str, list[int]] = {}
    by_surname: dict[str, list[int]] = {}

    for idx, c in enumerate(ordered_clues):
        for sid in sorted(c.strong_ids):
            by_strong.setdefault(sid, []).append(idx)
        for mrn in sorted(norm_mrns[idx]):
            by_mrn.setdefault(mrn, []).append(idx)
        if c.full_phonetic_name and len(c.name_tokens) >= 2:
            by_name.setdefault(c.full_phonetic_name, []).append(idx)
        if len(c.initial_tokens) >= 2:
            by_surname.setdefault(c.initial_tokens[-1], []).append(idx)

    # 1. Strong IDs (Aadhaar, ABHA, PAN, Phone, Email)
    for sid in sorted(by_strong):
        idxs = by_strong[sid]
        if len(idxs) > 1:
            anchor = idxs[0]
            for other in idxs[1:]:
                if _compatible(ordered_clues[anchor], ordered_clues[other]):
                    union(anchor, other, "MATCH_STRONG_ID")

    # 2. Hospital-scoped MRN / UHID
    for mrn in sorted(by_mrn):
        idxs = by_mrn[mrn]
        if len(idxs) > 1:
            anchor = idxs[0]
            for other in idxs[1:]:
                if _compatible(ordered_clues[anchor], ordered_clues[other]):
                    union(anchor, other, "MATCH_MRN")

    # 3. Corroborated full phonetic name + demographics (requires birth_year OR >=2 geo/age clues;
    #    never merges on age+village alone without birth_year/pin)
    for pname in sorted(by_name):
        idxs = by_name[pname]
        if len(idxs) < 2:
            continue
        for i_pos in range(len(idxs)):
            i = idxs[i_pos]
            ci = ordered_clues[i]
            for j_pos in range(i_pos + 1, len(idxs)):
                j = idxs[j_pos]
                cj = ordered_clues[j]
                if not _compatible(ci, cj):
                    continue
                score = 0
                has_strong_demog = False
                if ci.birth_year and cj.birth_year and ci.birth_year == cj.birth_year:
                    score += 2
                    has_strong_demog = True
                if ci.age is not None and cj.age is not None and ci.age == cj.age:
                    score += 1
                if ci.pin and cj.pin and ci.pin == cj.pin:
                    score += 1
                    has_strong_demog = True
                if ci.district and cj.district and ci.district.casefold() == cj.district.casefold():
                    score += 1
                if ci.village and cj.village and ci.village.casefold() == cj.village.casefold():
                    score += 1
                if has_strong_demog and score >= 3:
                    union(i, j, "MATCH_CORROBORATED_NAME")

    # 4. Initial / surname-first matching blocked by surname (requires exact birth_year + >=1 geo clue)
    for sname in sorted(by_surname):
        idxs = by_surname[sname]
        if len(idxs) < 2:
            continue
        for i_pos in range(len(idxs)):
            i = idxs[i_pos]
            ci = ordered_clues[i]
            for j_pos in range(i_pos + 1, len(idxs)):
                j = idxs[j_pos]
                cj = ordered_clues[j]
                if not _compatible(ci, cj):
                    continue
                if not names_match_with_initials(ci.initial_tokens, cj.initial_tokens):
                    continue
                if not (ci.birth_year and cj.birth_year and ci.birth_year == cj.birth_year):
                    continue
                geo_match = (
                    (ci.pin and cj.pin and ci.pin == cj.pin)
                    or (ci.district and cj.district and ci.district.casefold() == cj.district.casefold())
                    or (ci.village and cj.village and ci.village.casefold() == cj.village.casefold())
                )
                if geo_match:
                    union(i, j, "MATCH_INITIAL_CORROBORATED")

    clusters: dict[int, list[int]] = {}
    for idx in range(n):
        clusters.setdefault(find(idx), []).append(idx)

    # Track which clusters reference each strong_id/mrn so two separate clusters
    # sharing a family phone or local ID never collapse onto the same cluster_key.
    sid_to_clusters: dict[str, set[int]] = {}
    cluster_sids: dict[int, list[str]] = {}
    for root, members in clusters.items():
        sids = sorted({s for m in members for s in (ordered_clues[m].strong_ids | norm_mrns[m])})
        cluster_sids[root] = sids
        for s in sids:
            sid_to_clusters.setdefault(s, set()).add(root)

    result: dict[str, str | None] = {}
    for root, members in clusters.items():
        if len(members) == 1 and not ordered_clues[members[0]].has_strong_identity():
            ordered_clues[members[0]].decision_reason = "ABSTAIN_WEAK_EVIDENCE"
            result[ordered_clues[members[0]].record_id] = None
            continue
        sids = cluster_sids[root]
        if sids:
            shared_across_clusters = any(len(sid_to_clusters[s]) > 1 for s in sids[:3])
            if shared_across_clusters:
                # Disambiguate using the cluster's deterministic anchor record_id
                ckey = f"cluster|{ordered_clues[members[0]].record_id}|" + "|".join(sids[:2])
            else:
                ckey = "cluster|" + "|".join(sids[:3])
        else:
            ckey = "cluster|" + "|".join(sorted(ordered_clues[m].record_id for m in members)[:2])
        for m in members:
            if ordered_clues[m].decision_reason == "UNDECIDED":
                ordered_clues[m].decision_reason = "SINGLETON_STRONG_ID"
            result[ordered_clues[m].record_id] = ckey

    return result
