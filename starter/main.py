#!/usr/bin/env python3
"""RAKSHA / GuptKavach — Adversarial Healthcare Privacy Intelligence Engine.

Two-pass offline pipeline:
  Pass 1: Deterministic ingestion, corpus-level name & identity clue extraction,
          conservative cross-file clustering, and quasi-identifier group counting.
  Pass 2: Multilingual & context-aware PII redaction, hidden-channel sanitization
          (filenames, headers, metadata, keys, base64), FHIR R4 preservation,
          per-patient secret date shifting, age/location generalization, and export.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import io
import json
import os
import re
import sys
import time
from collections import Counter
from pathlib import Path

from raksha_engine.attacker import RecordProfile, simulate_attacks
from raksha_engine.clinical_validator import validate_fhir_r4_bundle
from raksha_engine.linking import (
    RecordClues,
    extract_clues_from_text,
    merge_clues,
    resolve_identities,
    set_name_clue,
)
from raksha_engine.mitigation import MitigationRecord, plan_record_mitigation
from raksha_engine.names import CorpusNameIndex, extract_names_from_text, is_clinical_phrase
from raksha_engine.patterns import classify_field, is_clinical_safe_field, normalize_digits
from raksha_engine.privacy import age_band, generalize_pin, pseudonym, shift_date_string
from raksha_engine.privacy_utility import (
    ClinicalUtilityMetrics,
    PrivacyMetrics,
    evaluate_release_gate,
)
from raksha_engine.qi_classifier import classify_field_tier
from raksha_engine.risk_engine import evaluate_corpus_risk
from raksha_engine.sanitizer import (
    sanitize_filename,
    sanitize_free_text,
    sanitize_json_node,
    sanitize_structured_cell,
)
from raksha_engine.crypto import GuptKavachKeyRing, InvalidSecretError
from raksha_engine.secure_fs import verify_path_containment
from raksha_engine.quarantine import QuarantineVault


def _peak_rss_mb() -> float:
    """Return process peak RSS in MB across Windows and POSIX without external deps."""
    try:
        import resource  # type: ignore[import-not-found]
        rss = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
        return round(rss / (1024 * 1024) if sys.platform == "darwin" else rss / 1024, 2)
    except ImportError:
        pass
    try:
        import ctypes
        import ctypes.wintypes as wt

        class _PMC(ctypes.Structure):
            _fields_ = [
                ("cb", wt.DWORD),
                ("PageFaultCount", wt.DWORD),
                ("PeakWorkingSetSize", ctypes.c_size_t),
                ("WorkingSetSize", ctypes.c_size_t),
                ("QuotaPeakPagedPoolUsage", ctypes.c_size_t),
                ("QuotaPagedPoolUsage", ctypes.c_size_t),
                ("QuotaPeakNonPagedPoolUsage", ctypes.c_size_t),
                ("QuotaNonPagedPoolUsage", ctypes.c_size_t),
                ("PagefileUsage", ctypes.c_size_t),
                ("PeakPagefileUsage", ctypes.c_size_t),
            ]

        pmc = _PMC()
        pmc.cb = ctypes.sizeof(_PMC)
        get_proc = ctypes.windll.kernel32.GetCurrentProcess
        get_proc.restype = wt.HANDLE
        hproc = get_proc()
        fn = getattr(ctypes.windll.kernel32, "K32GetProcessMemoryInfo", None) or getattr(
            ctypes.windll.psapi, "GetProcessMemoryInfo", None
        )
        if fn:
            fn.argtypes = [wt.HANDLE, ctypes.POINTER(_PMC), wt.DWORD]
            fn.restype = wt.BOOL
            if fn(hproc, ctypes.byref(pmc), pmc.cb):
                return round(pmc.PeakWorkingSetSize / (1024 * 1024), 2)
    except (AttributeError, OSError):
        pass
    return 0.0


def load_policy(path: Path) -> dict:
    """Tiny `key: value` reader for config/policy.yaml (no PyYAML needed)."""
    policy: dict = {}
    if path.exists():
        for line in path.read_text(encoding="utf-8").splitlines():
            line = line.split("#", 1)[0].strip()
            if ":" in line:
                k, v = (x.strip() for x in line.split(":", 1))
                if v.lstrip("-").isdigit():
                    policy[k] = int(v)
                else:
                    try:
                        policy[k] = float(v)
                    except ValueError:
                        policy[k] = v
    return policy


HERE = Path(__file__).resolve().parent
POLICY = load_policy(HERE / "config" / "policy.yaml")
SECRET = os.environ.get("RAKSHA_SECRET", "").encode("utf-8")


class Stats:
    identifiers = 0
    records = 0
    linked = 0
    generalized = 0
    suppressed = 0


def decode(raw: bytes) -> str | None:
    if raw.startswith(b"\xef\xbb\xbf"):
        return raw[3:].decode("utf-8", errors="strict")
    if raw.startswith((b"\xff\xfe", b"\xfe\xff")):
        return raw.decode("utf-16")
    for enc in ("utf-8", "cp1252"):
        try:
            return raw.decode(enc)
        except UnicodeDecodeError:
            continue
    return None


_NON_PERSON_FHIR_TYPES = {"Organization", "Location", "Practitioner", "Medication", "Substance", "Device"}


def _add_local_first(local_map: dict[str, set[str]], rid: str, raw_name: str) -> None:
    parts = raw_name.strip().split()
    if parts and len(parts[0]) >= 3 and not parts[0].isupper():
        local_map.setdefault(rid, set()).add(parts[0])


def _extract_json_clues(
    node,
    parent_key: str,
    clues: RecordClues,
    name_index: CorpusNameIndex,
    local_firsts: dict[str, set[str]] | None = None,
) -> None:
    if isinstance(node, str):
        kind = classify_field(parent_key)
        if kind in ("PATIENT_NAME", "RELATIVE_NAME"):
            if not is_clinical_phrase(node):
                name_index.add_name(node)
                if kind == "PATIENT_NAME":
                    set_name_clue(clues, node)
                    if local_firsts is not None:
                        _add_local_first(local_firsts, clues.record_id, node)
        elif kind == "DISTRICT":
            clues.district = node.strip()
        elif kind == "VILLAGE":
            clues.village = node.strip()
        elif kind == "GENDER":
            v = node.strip().upper()
            if v in ("M", "MALE", "F", "FEMALE"):
                clues.gender = v[0]
        elif kind == "AGE":
            m = re.search(r"\d+", normalize_digits(node))
            if m:
                clues.age = int(m.group(0))
        elif kind == "DOB":
            ym = re.search(r"(19\d{2}|20\d{2})", node)
            if ym:
                clues.birth_year = int(ym.group(1))
        merge_clues(clues, extract_clues_from_text(clues.record_id, node))
        extract_names_from_text(node, name_index)
    elif isinstance(node, int) and not isinstance(node, bool):
        if classify_field(parent_key) == "AGE":
            clues.age = node
    elif isinstance(node, list):
        for item in node:
            _extract_json_clues(item, parent_key, clues, name_index, local_firsts)
    elif isinstance(node, dict):
        rtype = node.get("resourceType")
        if rtype == "Patient":
            for nm in node.get("name") or []:
                if isinstance(nm, dict) and nm.get("text"):
                    name_index.add_name(str(nm["text"]))
                    set_name_clue(clues, str(nm["text"]))
                    if local_firsts is not None:
                        _add_local_first(local_firsts, clues.record_id, str(nm["text"]))
            for ct in node.get("contact") or []:
                if isinstance(ct, dict) and isinstance(ct.get("name"), dict) and ct["name"].get("text"):
                    name_index.add_name(str(ct["name"]["text"]))
            if node.get("gender"):
                clues.gender = str(node["gender"])[0].upper()
        for k, v in node.items():
            if rtype in _NON_PERSON_FHIR_TYPES and k == "name":
                continue
            if rtype == "Patient" and k == "contact":
                continue
            _extract_json_clues(v, k, clues, name_index, local_firsts)


def _qi_signature(clues: RecordClues, width: int = 5) -> tuple[str, str] | None:
    if clues.age is not None and clues.district:
        return (age_band(clues.age, width), clues.district.casefold())
    return None


def main() -> int:
    ap = argparse.ArgumentParser(description="RAKSHA / GuptKavach privacy pipeline")
    ap.add_argument("--input", required=True)
    ap.add_argument("--output", required=True)
    a = ap.parse_args()

    Stats.identifiers = 0
    Stats.records = 0
    Stats.linked = 0
    Stats.generalized = 0
    Stats.suppressed = 0

    t0 = time.monotonic()
    inp, out = Path(a.input.strip("'\"")).resolve(), Path(a.output.strip("'\"")).resolve()
    san = out / "sanitized"
    san.mkdir(parents=True, exist_ok=True)
    keyring = GuptKavachKeyRing(SECRET) if SECRET else None

    max_days = int(POLICY.get("date_shift_max_days", 180))
    min_group = int(POLICY.get("min_group_size", 5))
    sys.setrecursionlimit(5000)

    # ------------------------------------------------------------------
    # PASS 1: Read, validate, extract names & identity clues
    # ------------------------------------------------------------------
    parsed_files: list[dict] = []
    name_index = CorpusNameIndex()
    all_clues: list[RecordClues] = []
    local_firsts: dict[str, set[str]] = {}
    field_tier_counts: Counter[str] = Counter()
    stage_trace: list[dict[str, object]] = []

    for path in sorted(p for p in inp.rglob("*") if p.is_file()):
        try:
            canonical_path = verify_path_containment(path, inp)
        except Exception:
            continue
        rel = canonical_path.relative_to(inp).as_posix()
        raw = canonical_path.read_bytes()
        sha = hashlib.sha256(raw).hexdigest()
        ext = canonical_path.suffix.lower()
        item: dict = {"rel": rel, "sha": sha, "ext": ext, "status": "ok"}

        try:
            if ext not in (".csv", ".tsv", ".json", ".txt"):
                raise ValueError("unsupported_format")
            if not raw.strip():
                raise ValueError("empty_file")
            text = decode(raw)
            if text is None:
                raise ValueError("undecodable_text")

            if ext in (".csv", ".tsv"):
                delim = "\t" if ext == ".tsv" else ","
                rows = list(csv.reader(io.StringIO(text, newline=""), delimiter=delim))
                item["kind"] = "csv"
                item["delim"] = delim
                item["rows"] = rows
                if rows:
                    header, body = rows[0], rows[1:]
                    for h in header:
                        field_tier_counts[classify_field_tier(h).category.value] += 1
                    col_kinds = [classify_field(h) for h in header]
                    item["col_kinds"] = col_kinds
                    for i, row in enumerate(body):
                        rid = f"{rel}::row:{i}"
                        clues = extract_clues_from_text(rid, delim.join(row))
                        for c_idx, cell in enumerate(row):
                            ck = col_kinds[c_idx] if c_idx < len(col_kinds) else None
                            if ck in ("PATIENT_NAME", "RELATIVE_NAME") and cell.strip():
                                if not is_clinical_phrase(cell):
                                    name_index.add_name(cell)
                                    if ck == "PATIENT_NAME":
                                        set_name_clue(clues, cell)
                                        _add_local_first(local_firsts, rid, cell)
                            elif ck == "DISTRICT" and cell.strip():
                                clues.district = cell.strip()
                            elif ck == "VILLAGE" and cell.strip():
                                clues.village = cell.strip()
                            elif ck == "GENDER" and cell.strip():
                                g = cell.strip().upper()
                                if g in ("M", "MALE", "F", "FEMALE"):
                                    clues.gender = g[0]
                            elif ck == "AGE" and cell.strip():
                                m = re.search(r"\d+", normalize_digits(cell))
                                if m:
                                    clues.age = int(m.group(0))
                            elif ck == "DOB" and cell.strip():
                                ym = re.search(r"(19\d{2}|20\d{2})", cell)
                                if ym:
                                    clues.birth_year = int(ym.group(1))
                            extract_names_from_text(cell, name_index)
                        all_clues.append(clues)

            elif ext == ".json":
                data = json.loads(text)
                item["kind"] = "json"
                item["data"] = data
                has_top_patient = isinstance(data, dict) and (
                    "patient" in data
                    or any(
                        classify_field(k) in ("PATIENT_NAME", "MRN", "PHONE", "AADHAAR", "ABHA_NUMBER")
                        for k in data.keys()
                    )
                )
                is_doc = (
                    not isinstance(data, dict)
                    or data.get("resourceType") == "Bundle"
                    or has_top_patient
                    or not any(isinstance(v, list) and v and all(isinstance(x, dict) for x in v) for v in data.values())
                )
                item["is_doc"] = is_doc
                if is_doc:
                    rid = f"{rel}::doc"
                    clues = RecordClues(record_id=rid)
                    _extract_json_clues(data, "", clues, name_index, local_firsts)
                    # Multi-patient index/summary JSONs (e.g. by_uhid / by_name) must not merge distinct patients
                    is_multi_index = (
                        isinstance(data, dict)
                        and data.get("resourceType") != "Bundle"
                        and (len(clues.mrns) > 1 or len(clues.strong_ids) > 3)
                    )
                    if is_multi_index:
                        clues.strong_ids.clear()
                        clues.mrns.clear()
                        clues.name_tokens.clear()
                        clues.full_phonetic_name = ""
                    else:
                        merge_clues(clues, extract_clues_from_text(rid, rel))
                    all_clues.append(clues)
                else:
                    for k, v in data.items():
                        if isinstance(v, list) and v and all(isinstance(x, dict) for x in v):
                            for i, obj in enumerate(v):
                                ptr = "/" + k.replace("~", "~0").replace("/", "~1") + f"/{i}"
                                rid = f"{rel}::{ptr}"
                                clues = RecordClues(record_id=rid)
                                _extract_json_clues(obj, k, clues, name_index, local_firsts)
                                all_clues.append(clues)
            else:
                item["kind"] = "txt"
                item["text"] = text
                rid = f"{rel}::doc"
                txt_names = CorpusNameIndex()
                extract_names_from_text(text, txt_names)
                for fn in txt_names.first_names:
                    name_index.first_names.add(fn)
                    local_firsts.setdefault(rid, set()).add(fn)
                for full_n in txt_names.full_names:
                    name_index.add_name(full_n)
                clues = extract_clues_from_text(rid, text)
                if txt_names.full_names:
                    set_name_clue(clues, sorted(txt_names.full_names)[0])
                all_clues.append(clues)

        except (ValueError, RecursionError, UnicodeError, csv.Error) as exc:
            reason = str(exc) if isinstance(exc, ValueError) and str(exc).isidentifier() else type(exc).__name__
            item["status"] = "quarantined"
            item["reason"] = reason

        parsed_files.append(item)

    stage_trace.append({"stage": "ingestion_and_extraction", "status": "ok", "files": len(parsed_files), "records": len(all_clues)})

    # Resolve patient clusters globally
    cluster_map = resolve_identities(all_clues)
    clues_by_rid = {c.record_id: c for c in all_clues}
    stage_trace.append({"stage": "identity_resolution", "status": "ok", "clusters": len({v for v in cluster_map.values() if v})})

    # Share first names across records in the same patient cluster (for notes like "Irfan ka BP")
    cluster_firsts: dict[str, set[str]] = {}
    for rid, fset in local_firsts.items():
        ckey = cluster_map.get(rid)
        if ckey:
            cluster_firsts.setdefault(ckey, set()).update(fset)

    def _firsts_for(rid: str, ckey: str | None) -> set[str] | None:
        s: set[str] = set()
        if rid in local_firsts:
            s.update(local_firsts[rid])
        if ckey and ckey in cluster_firsts:
            s.update(cluster_firsts[ckey])
        return s or None

    # Compute quasi-identifier group sizes & pre-mitigation adversarial risk
    qi_counts: Counter[tuple[str, str]] = Counter()
    for c in all_clues:
        sig = _qi_signature(c)
        if sig:
            qi_counts[sig] += 1

    cluster_sizes: Counter[str] = Counter(v for v in cluster_map.values() if v)
    pre_profiles: list[RecordProfile] = []
    for c in all_clues:
        ck = cluster_map.get(c.record_id)
        pre_profiles.append(
            RecordProfile(
                record_id=c.record_id,
                patient_key=ck or c.record_id,
                age_val=str(c.age) if c.age is not None else "",
                birth_year=str(c.birth_year) if c.birth_year else "",
                gender=c.gender,
                district=c.district.casefold() if c.district else "",
                village_or_loc=c.village.casefold() if c.village else "",
                pin=c.pin,
                record_count=cluster_sizes.get(ck, 1) if ck else 1,
            )
        )
    pre_attack = simulate_attacks(pre_profiles, min_group_size=min_group)
    pre_risk = evaluate_corpus_risk(pre_profiles, POLICY)
    stage_trace.append({"stage": "pre_mitigation_risk_and_attack", "status": "ok", "uniquely_distinguishable": pre_attack.uniquely_distinguishable_records})
    post_profiles: list[RecordProfile] = []
    mitigation_actions: Counter[str] = Counter()

    def _apply_mitigation_and_record(rid: str, ckey: str | None) -> bool:
        c_obj = clues_by_rid.get(rid)
        sig = _qi_signature(c_obj) if c_obj else None
        assess = pre_risk.assessments.get(rid)
        rare = bool(
            (sig and qi_counts[sig] < min_group)
            or (assess and (assess.below_min_group or assess.risk_category in ("HIGH", "CRITICAL")))
        )
        if c_obj and assess:
            plan = plan_record_mitigation(
                assess,
                POLICY,
                has_age=c_obj.age is not None,
                has_date=bool(c_obj.birth_year),
                has_pin=bool(c_obj.pin),
                has_district=bool(c_obj.district),
                has_village=bool(c_obj.village),
            )
            for mr in plan.records:
                mitigation_actions[mr.action] += 1
            if any(mr.action.startswith("SUPPRESS_") for mr in plan.records):
                Stats.suppressed += 1
            ck = ckey or rid
            post_profiles.append(
                RecordProfile(
                    record_id=rid,
                    patient_key=ck,
                    age_val=age_band(c_obj.age, width=plan.age_band_width) if c_obj.age is not None else "",
                    birth_year="",  # exact birthDate shifted or redacted
                    gender=c_obj.gender,
                    district="" if (rare and plan.suppress_district) else (c_obj.district.casefold() if c_obj.district else ""),
                    village_or_loc="",  # village/locality always suppressed
                    pin="" if rare else (generalize_pin(c_obj.pin) if c_obj.pin else ""),
                    record_count=cluster_sizes.get(ckey, 1) if ckey else 1,
                )
            )
        return rare

    # ------------------------------------------------------------------
    # PASS 2: Sanitize and export
    # ------------------------------------------------------------------
    files_report: list[dict] = []
    records: list[dict] = []
    used_out_paths: set[str] = set()
    fhir_bundles_checked = 0
    fhir_resources_checked = 0
    fhir_failures: list[dict[str, str]] = []

    for item in parsed_files:
        rel = item["rel"]
        sha = item["sha"]
        entry: dict = {"input_sha256": sha}

        if item["status"] == "quarantined":
            entry.update(output=None, status="quarantined", reason=item["reason"])
            files_report.append(entry)
            continue

        # Sanitize filename if it contains PII
        out_rel = sanitize_filename(rel, name_index, sha)
        if out_rel in used_out_paths:
            p = Path(out_rel)
            out_rel = (p.parent / f"{p.stem}_{sha[:6]}{p.suffix}").as_posix()
        used_out_paths.add(out_rel)

        try:
            kind = item["kind"]
            if kind == "csv":
                rows = item["rows"]
                delim = item["delim"]
                if not rows:
                    out_text = ""
                else:
                    header, body = rows[0], rows[1:]
                    col_kinds = item["col_kinds"]
                    clean_header = []
                    for h in header:
                        ch, nh = sanitize_free_text(
                            h, name_index, None, SECRET, max_days, decode_b64=False,
                            local_first_names=name_index.first_names,
                        )
                        Stats.identifiers += nh
                        clean_header.append(ch)
                    buf = io.StringIO()
                    w = csv.writer(buf, delimiter=delim, lineterminator="\n")
                    w.writerow(clean_header)

                    for i, row in enumerate(body):
                        rid = f"{rel}::row:{i}"
                        ckey = cluster_map.get(rid)
                        pid = pseudonym(ckey, SECRET) if ckey else None
                        rare = _apply_mitigation_and_record(rid, ckey)

                        out_row: list[str] = []
                        row_gen = False
                        for c_idx, cell in enumerate(row):
                            ck = col_kinds[c_idx] if c_idx < len(col_kinds) else None
                            csafe = is_clinical_safe_field(header[c_idx]) if c_idx < len(header) else False
                            nc, n_id, g = sanitize_structured_cell(
                                ck, cell, name_index, ckey or rid, pid, SECRET, max_days,
                                rare_suppress=rare, clinical_safe=csafe, local_first_names=_firsts_for(rid, ckey),
                            )
                            Stats.identifiers += n_id
                            row_gen = row_gen or g
                            out_row.append(nc)

                        # Ensure pid appears inside the exported row when linked
                        if pid and pid not in out_row:
                            for c_idx, ck in enumerate(col_kinds):
                                if ck == "PATIENT_NAME" and c_idx < len(out_row):
                                    out_row[c_idx] = pid
                                    break

                        w.writerow(out_row)
                        if row_gen:
                            Stats.generalized += 1
                        records.append({"file": f"sanitized/{out_rel}", "loc": f"row:{i}", "patient": pid})
                        Stats.records += 1
                        if pid:
                            Stats.linked += 1
                    out_text = buf.getvalue()

            elif kind == "json":
                data = item["data"]
                is_doc = item["is_doc"]
                if is_doc:
                    rid = f"{rel}::doc"
                    ckey = cluster_map.get(rid)
                    pid = pseudonym(ckey, SECRET) if ckey else None
                    rare = _apply_mitigation_and_record(rid, ckey)

                    clean_data, n_id, gen = sanitize_json_node(
                        data, "", name_index, ckey or rid, pid, SECRET, max_days,
                        rare_suppress=rare, local_first_names=_firsts_for(rid, ckey),
                    )
                    Stats.identifiers += n_id
                    if gen:
                        Stats.generalized += 1
                    records.append({"file": f"sanitized/{out_rel}", "loc": "doc", "patient": pid})
                    Stats.records += 1
                    if pid:
                        Stats.linked += 1
                else:
                    clean_data = {}
                    for k, v in data.items():
                        clean_k, nk = sanitize_free_text(k, name_index, None, SECRET, max_days, decode_b64=False)
                        Stats.identifiers += nk
                        if isinstance(v, list) and v and all(isinstance(x, dict) for x in v):
                            new_list = []
                            ptr_k = k.replace("~", "~0").replace("/", "~1")
                            for i, obj in enumerate(v):
                                ptr = f"/{ptr_k}/{i}"
                                rid = f"{rel}::{ptr}"
                                ckey = cluster_map.get(rid)
                                pid = pseudonym(ckey, SECRET) if ckey else None
                                rare = _apply_mitigation_and_record(rid, ckey)

                                c_obj_out, n_id, gen = sanitize_json_node(
                                    obj, k, name_index, ckey or rid, pid, SECRET, max_days,
                                    rare_suppress=rare, local_first_names=_firsts_for(rid, ckey),
                                )
                                Stats.identifiers += n_id
                                if gen:
                                    Stats.generalized += 1
                                new_list.append(c_obj_out)
                                records.append({"file": f"sanitized/{out_rel}", "loc": ptr, "patient": pid})
                                Stats.records += 1
                                if pid:
                                    Stats.linked += 1
                            clean_data[clean_k] = new_list
                        else:
                            c_v, n_id, gen = sanitize_json_node(
                                v, k, name_index, f"{rel}::meta", None, SECRET, max_days, rare_suppress=False
                            )
                            Stats.identifiers += n_id
                            clean_data[clean_k] = c_v
                if isinstance(clean_data, dict) and clean_data.get("resourceType") == "Bundle":
                    fres = validate_fhir_r4_bundle(clean_data, location=out_rel)
                    fhir_bundles_checked += fres.bundles_checked
                    fhir_resources_checked += fres.resources_checked
                    for fl in fres.failures:
                        fhir_failures.append({"code": fl.code, "location": fl.location, "detail": fl.detail})
                out_text = json.dumps(clean_data, ensure_ascii=False, indent=2) + "\n"

            else:  # txt
                rid = f"{rel}::doc"
                ckey = cluster_map.get(rid)
                pid = pseudonym(ckey, SECRET) if ckey else None
                _apply_mitigation_and_record(rid, ckey)
                out_text, n_id = sanitize_free_text(
                    item["text"], name_index, ckey or rid, SECRET, max_days,
                    local_first_names=_firsts_for(rid, ckey),
                )
                Stats.identifiers += n_id
                if pid and pid not in out_text:
                    out_text = f"Patient: {pid}\n" + out_text
                records.append({"file": f"sanitized/{out_rel}", "loc": "doc", "patient": pid})
                Stats.records += 1
                if pid:
                    Stats.linked += 1

            dest = san / out_rel
            dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_text(out_text, encoding="utf-8", newline="")
            entry.update(output=f"sanitized/{out_rel}", status="sanitized")

        except (ValueError, RecursionError, UnicodeError, csv.Error) as exc:
            reason = str(exc) if isinstance(exc, ValueError) and str(exc).isidentifier() else type(exc).__name__
            entry.update(output=None, status="quarantined", reason=reason)

        files_report.append(entry)

    exported = {e["output"] for e in files_report if e["output"]}
    records = [r for r in records if r["file"] in exported]

    with open(out / "records.jsonl", "w", encoding="utf-8") as f:
        for r in records:
            f.write(json.dumps(r, ensure_ascii=False, sort_keys=True) + "\n")

    n_san = sum(e["status"] == "sanitized" for e in files_report)
    n_linked = sum(r["patient"] is not None for r in records)
    post_attack = simulate_attacks(post_profiles, min_group_size=min_group)
    post_risk = evaluate_corpus_risk(post_profiles, POLICY)
    priv_metrics = PrivacyMetrics(
        direct_identifiers_detected=Stats.identifiers,
        pre_attack_successes=sum(pre_attack.strategy_success_counts.values()),
        post_attack_successes=sum(post_attack.strategy_success_counts.values()),
        pre_uniquely_distinguishable=pre_attack.uniquely_distinguishable_records,
        post_uniquely_distinguishable=post_attack.uniquely_distinguishable_records,
        unique_candidate_groups=post_risk.unique_candidate_groups,
        records_below_min_group=post_risk.records_below_min_group,
        generalizations_applied=Stats.generalized,
        suppressions_applied=Stats.suppressed,
        files_quarantined=len(files_report) - n_san,
    )
    util_metrics = ClinicalUtilityMetrics(records_processed=len(records), records_linked=n_linked)
    gate = evaluate_release_gate(priv_metrics, util_metrics, post_risk, pre_attack, post_attack, POLICY)
    stage_trace.append({"stage": "sanitization_validation_and_gate", "status": gate.status, "fhir_bundles": fhir_bundles_checked})

    report = {
        "schema": "raksha-report/1",
        "files": files_report,
        "counts": {
            "files_total": len(files_report),
            "files_sanitized": n_san,
            "files_quarantined": len(files_report) - n_san,
            "records_processed": len(records),
            "identifiers_detected": Stats.identifiers,
            "records_linked": n_linked,
            "records_generalized": Stats.generalized,
            "records_suppressed": Stats.suppressed,
            "records_quarantined": 0,
        },
        "privacy_intelligence": {
            "policy_version": gate.policy_version,
            "release_gate": {
                "status": gate.status,
                "reason_codes": gate.reason_codes,
                "risk_categories": gate.risk_categories,
                "affected_record_counts": gate.affected_record_counts,
                "recommended_mitigation": gate.recommended_mitigation,
            },
            "attack_simulation": {
                "strategies": pre_attack.strategies_run,
                "pre_uniquely_distinguishable": pre_attack.uniquely_distinguishable_records,
                "post_uniquely_distinguishable": post_attack.uniquely_distinguishable_records,
                "pre_attack_successes": pre_attack.strategy_success_counts,
                "post_attack_successes": post_attack.strategy_success_counts,
            },
            "risk_summary": {
                "pre_categories": pre_risk.category_counts,
                "post_categories": post_risk.category_counts,
                "records_below_min_group_pre": pre_risk.records_below_min_group,
                "records_below_min_group_post": post_risk.records_below_min_group,
                "unique_candidate_groups_post": post_risk.unique_candidate_groups,
                "note": "estimated_risk_score is a structural index (0-100), distinct from measured group size k",
            },
            "mitigation_actions": dict(sorted(mitigation_actions.items())),
            "field_tier_counts": dict(sorted(field_tier_counts.items())),
            "stage_trace": stage_trace,
        },
        "clinical_integrity": {
            "fhir_bundles_checked": fhir_bundles_checked,
            "fhir_resources_checked": fhir_resources_checked,
            "fhir_validation_passed": len(fhir_failures) == 0,
            "fhir_failures": fhir_failures[:20],
        },
        "timing": {"seconds": round(time.monotonic() - t0, 2)},
        "resources": {"peak_rss_mb": _peak_rss_mb()},
    }
    (out / "report.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(f"files {len(files_report)} sanitized {n_san} quarantined {len(files_report) - n_san} records {len(records)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
