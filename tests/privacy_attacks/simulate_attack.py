"""Phase 3: Deterministic Re-identification Attack Simulator.

Simulates an adversary with auxiliary voter-list registry + known facts
(without access to RAKSHA_SECRET or truth.json) attacking both raw input
and GuptKavach sanitized output.
"""
from __future__ import annotations

import csv
import datetime as dt
import json
import re
from collections import Counter, defaultdict
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
REGISTRY_PATH = REPO_ROOT / "dev" / "attacker" / "registry.csv"
KNOWN_FACTS_PATH = REPO_ROOT / "dev" / "attacker" / "known_facts.jsonl"


def load_registry() -> list[dict]:
    rows = []
    with open(REGISTRY_PATH, encoding="utf-8") as f:
        for r in csv.DictReader(f):
            rows.append(r)
    return rows


def load_known_facts() -> list[dict]:
    facts = []
    with open(KNOWN_FACTS_PATH, encoding="utf-8") as f:
        for line in f:
            if line.strip():
                facts.append(json.loads(line))
    return facts


def _age_in_band(age: int, band_str: str) -> bool:
    if band_str == "85+":
        return age >= 85
    m = re.fullmatch(r"(\d+)-(\d+)", band_str.strip())
    if m:
        return int(m.group(1)) <= age <= int(m.group(2))
    if band_str.isdigit():
        return abs(age - int(band_str)) <= 1
    return False


def _extract_records_from_dir(root: Path) -> list[dict]:
    """Extract observable quasi-identifiers & direct clues from CSV/JSON/TXT."""
    recs = []
    for p in sorted(root.rglob("*")):
        if not p.is_file():
            continue
        ext = p.suffix.lower()
        if ext in (".csv", ".tsv"):
            delim = "\t" if ext == ".tsv" else ","
            try:
                raw = p.read_bytes()
                if raw.startswith((b"\xff\xfe", b"\xfe\xff")):
                    txt = raw.decode("utf-16")
                elif raw.startswith(b"\xef\xbb\xbf"):
                    txt = raw[3:].decode("utf-8")
                else:
                    try:
                        txt = raw.decode("utf-8")
                    except UnicodeDecodeError:
                        txt = raw.decode("cp1252", errors="ignore")
                rows = list(csv.DictReader(txt.splitlines(), delimiter=delim))
                for r in rows:
                    rec = {
                        "file": p.relative_to(root).as_posix(),
                        "gender": "",
                        "age": "",
                        "village": "",
                        "district": "",
                        "pin": "",
                        "phone": "",
                        "name": "",
                        "pid": "",
                    }
                    for k, v in r.items():
                        if not k or not v:
                            continue
                        kl = k.casefold()
                        if "gender" in kl or "sex" in kl or "ling" in kl:
                            rec["gender"] = v.strip()[:1].upper()
                        elif "age" in kl or "umar" in kl:
                            rec["age"] = v.strip()
                        elif "village" in kl or "gaon" in kl or "city" in kl:
                            if not v.startswith("["):
                                rec["village"] = v.strip()
                        elif "district" in kl or "jila" in kl:
                            if not v.startswith("["):
                                rec["district"] = v.strip()
                        elif "pin" in kl or "zip" in kl:
                            if not v.startswith("["):
                                rec["pin"] = v.strip()
                        elif "mobile" in kl or "phone" in kl:
                            if not v.startswith("["):
                                rec["phone"] = re.sub(r"\D", "", v)[-10:]
                        elif "name" in kl or "naam" in kl:
                            if v.startswith("PSN-"):
                                rec["pid"] = v.strip()
                            elif not v.startswith("["):
                                rec["name"] = v.strip()
                        elif "uhid" in kl or "patientid" in kl:
                            if v.startswith("PSN-"):
                                rec["pid"] = v.strip()
                    recs.append(rec)
            except Exception:
                continue
    return recs


def attack_records(records: list[dict], registry: list[dict]) -> dict:
    """Run Sweeney-style demographic + quasi-identifier linkage against registry."""
    total = len(records)
    vulnerable = 0
    unique_reid = 0
    protected_by_gen = 0

    for rec in records:
        if not (rec["gender"] or rec["age"] or rec["district"] or rec["village"] or rec["pin"]):
            continue
        cands = registry
        if rec["phone"]:
            cands = [r for r in cands if r.get("phone", "").endswith(rec["phone"])]
        if rec["gender"] in ("M", "F"):
            cands = [r for r in cands if r.get("gender", "").upper() == rec["gender"]]
        if rec["age"]:
            filtered = [r for r in cands if r.get("age", "").isdigit() and _age_in_band(int(r["age"]), rec["age"])]
            if filtered:
                cands = filtered
        if rec["district"]:
            filtered = [r for r in cands if r.get("district", "").casefold() == rec["district"].casefold()]
            if filtered:
                cands = filtered
        if rec["village"]:
            filtered = [r for r in cands if r.get("village", "").casefold() == rec["village"].casefold()]
            if filtered:
                cands = filtered
        if rec["pin"] and "*" not in rec["pin"]:
            filtered = [r for r in cands if r.get("pin", "") == rec["pin"]]
            if filtered:
                cands = filtered
        elif rec["pin"] and "*" in rec["pin"]:
            pref = rec["pin"].replace("*", "")
            filtered = [r for r in cands if r.get("pin", "").startswith(pref)]
            if filtered:
                cands = filtered

        if len(cands) == 1:
            unique_reid += 1
            vulnerable += 1
        elif 1 < len(cands) <= 2:
            vulnerable += 1
        else:
            protected_by_gen += 1

    # Profile aggregation by PSN-XXXXXX
    profiles: dict[str, list[dict]] = defaultdict(list)
    for rec in records:
        if rec["pid"]:
            profiles[rec["pid"]].append(rec)

    profile_reid = 0
    for pid, precs in profiles.items():
        # Merge QIs across profile
        genders = {r["gender"] for r in precs if r["gender"]}
        districts = {r["district"] for r in precs if r["district"]}
        ages = [r["age"] for r in precs if r["age"]]
        cands = registry
        if len(genders) == 1:
            g = next(iter(genders))
            cands = [r for r in cands if r.get("gender", "").upper() == g]
        if len(districts) == 1:
            d = next(iter(districts))
            f = [r for r in cands if r.get("district", "").casefold() == d.casefold()]
            if f:
                cands = f
        if ages:
            f = [r for r in cands if r.get("age", "").isdigit() and _age_in_band(int(r["age"]), ages[0])]
            if f:
                cands = f
        if len(cands) == 1:
            profile_reid += 1

    return {
        "total_csv_records": total,
        "unique_reidentifications": unique_reid,
        "vulnerable_records_k_le_2": vulnerable,
        "protected_by_generalization": protected_by_gen,
        "attack_success_rate_pct": round(100.0 * vulnerable / max(1, total), 2),
        "profiles_attacked": len(profiles),
        "profiles_uniquely_reidentified": profile_reid,
    }


def check_known_facts_los(sanitized_root: Path, known_facts: list[dict]) -> dict:
    """Test Attack 3: Rare diagnosis + length of stay / visit date matching."""
    # Check how many known_facts exact visit_dates appear unshifted in sanitized/
    all_text = ""
    for p in sanitized_root.rglob("*"):
        if p.is_file():
            all_text += "\n" + p.read_text(encoding="utf-8", errors="replace")

    exact_date_hits = 0
    for kf in known_facts:
        vd = kf.get("visit_date", "")
        if vd and vd in all_text:
            exact_date_hits += 1
    return {
        "known_facts_total": len(known_facts),
        "unshifted_exact_iso_date_hits": exact_date_hits,
    }


def main() -> int:
    registry = load_registry()
    known_facts = load_known_facts()

    raw_recs = _extract_records_from_dir(REPO_ROOT / "dev" / "input")
    san_dir = REPO_ROOT / "my_output_m8" / "sanitized"
    san_recs = _extract_records_from_dir(san_dir)

    raw_res = attack_records(raw_recs, registry)
    san_res = attack_records(san_recs, registry)
    kf_raw = check_known_facts_los(REPO_ROOT / "dev" / "input", known_facts)
    kf_san = check_known_facts_los(san_dir, known_facts)

    print("=== RE-IDENTIFICATION ATTACK SIMULATOR ===")
    print("Registry size:", len(registry), "| Known facts:", len(known_facts))
    print("\n[RAW INPUT]:", json.dumps(raw_res, indent=2))
    print("[RAW KNOWN-FACTS DATE HITS]:", json.dumps(kf_raw, indent=2))
    print("\n[GUPTKAVACH SANITIZED]:", json.dumps(san_res, indent=2))
    print("[SANITIZED KNOWN-FACTS DATE HITS]:", json.dumps(kf_san, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
