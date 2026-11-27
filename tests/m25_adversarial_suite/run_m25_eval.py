#!/usr/bin/env python3
"""M25 Independent Adversarial Evaluation Runner (Phases 2-7).

Runs starter/main.py offline against independent synthetic benchmarks and
outputs exact, unrounded metrics per split and per attack category.
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import time
import tracemalloc
import unicodedata
from collections import defaultdict
from pathlib import Path
from typing import Any, Dict, List, Tuple

REPO_ROOT = Path(__file__).resolve().parents[2]
STARTER_MAIN = REPO_ROOT / "starter" / "main.py"
VALIDATE_OUT = REPO_ROOT / "validate_output.py"

sys.path.insert(0, str(Path(__file__).resolve().parent))
from m25_generator import generate_adversarial_15, generate_large_split


def _norm(s: str) -> str:
    return " ".join(unicodedata.normalize("NFKC", s).casefold().split())


def _run_engine(in_dir: Path, out_dir: Path, secret: str = "m25-eval-secret") -> Tuple[float, Dict[str, Any], List[Dict[str, Any]], str]:
    env = os.environ.copy()
    env["RAKSHA_SECRET"] = secret
    env["HF_HUB_OFFLINE"] = "1"
    env["TRANSFORMERS_OFFLINE"] = "1"
    t0 = time.perf_counter()
    res = subprocess.run(
        [sys.executable, str(STARTER_MAIN), "--input", str(in_dir), "--output", str(out_dir)],
        capture_output=True,
        text=True,
        env=env,
    )
    rt = time.perf_counter() - t0
    if res.returncode != 0:
        raise RuntimeError(f"Engine failed ({res.returncode}): {res.stderr}")
    val = subprocess.run(
        [sys.executable, str(VALIDATE_OUT), "--input", str(in_dir), "--output", str(out_dir)],
        capture_output=True,
        text=True,
    )
    report = json.loads((out_dir / "report.json").read_text(encoding="utf-8"))
    recs = [
        json.loads(line)
        for line in (out_dir / "records.jsonl").read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    return rt, report, recs, val.stdout.strip()


def _collect_san_text_and_paths(out_dir: Path) -> Tuple[str, List[str]]:
    texts = []
    paths = []
    san = out_dir / "sanitized"
    for p in san.rglob("*"):
        if p.is_file():
            rel = p.relative_to(san).as_posix()
            paths.append(rel)
            texts.append(p.read_text(encoding="utf-8", errors="ignore"))
    return _norm("\n".join(texts + paths)), paths


def eval_large_split(split_name: str, seed: int) -> Dict[str, Any]:
    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        meta = generate_large_split(tmp_path, split_name, seed=seed, num_records=600)
        in_dir = tmp_path / split_name
        out_dir = tmp_path / f"out_{split_name}"
        rt, report, recs, contract = _run_engine(in_dir, out_dir, secret=f"m25-{split_name}")
        all_norm, _ = _collect_san_text_and_paths(out_dir)

        leaked_by_cat: Dict[str, int] = defaultdict(int)
        tot_by_cat: Dict[str, int] = defaultdict(int)
        leaked_examples: List[Tuple[str, str, str]] = []
        for cat, val, fmt in meta["pii_probes"]:
            tot_by_cat[cat] += 1
            if _norm(val) in all_norm:
                leaked_by_cat[cat] += 1
                if len(leaked_examples) < 15:
                    leaked_examples.append((cat, fmt, val))

        pii_total = len(meta["pii_probes"])
        pii_leaked = sum(leaked_by_cat.values())
        pii_tp = pii_total - pii_leaked

        clin_total = len(meta["clinical_probes"])
        clin_preserved = 0
        clin_missing = []
        for cp in meta["clinical_probes"]:
            if _norm(cp) in all_norm:
                clin_preserved += 1
            else:
                if len(clin_missing) < 10:
                    clin_missing.append(cp)

        fp = clin_total - clin_preserved
        prec = pii_tp / (pii_tp + fp) if (pii_tp + fp) else 1.0
        rec = pii_tp / pii_total if pii_total else 1.0
        f1 = (2 * prec * rec) / (prec + rec) if (prec + rec) else 0.0

        return {
            "split": split_name,
            "seed": seed,
            "records": meta["records"],
            "runtime_secs": round(rt, 3),
            "contract": contract,
            "files_total": report["counts"]["files_total"],
            "files_sanitized": report["counts"]["files_sanitized"],
            "files_quarantined": report["counts"]["files_quarantined"],
            "pii_total": pii_total,
            "pii_detected_and_removed": pii_tp,
            "pii_leaked": pii_leaked,
            "pii_precision": prec,
            "pii_recall": rec,
            "pii_f1": f1,
            "leaked_by_category": dict(leaked_by_cat),
            "total_by_category": dict(tot_by_cat),
            "leaked_examples": leaked_examples,
            "clinical_total": clin_total,
            "clinical_preserved": clin_preserved,
            "clinical_missing_count": fp,
            "clinical_missing_examples": clin_missing,
        }


def eval_adversarial_15() -> Dict[str, Any]:
    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        adv = generate_adversarial_15(tmp_path)
        in_dir = adv["dir"]
        out_dir = tmp_path / "out_adv"
        rt, report, _, contract = _run_engine(in_dir, out_dir, secret="m25-adv-15")
        all_norm, san_paths = _collect_san_text_and_paths(out_dir)

        # Map input sha256 -> output path for per-file checks
        sha_to_out = {e.get("input_sha256"): e.get("output") for e in report.get("files", [])}
        import hashlib
        per_cat = {}
        for c in adv["cases"]:
            src = in_dir / c["file"]
            sha = hashlib.sha256(src.read_bytes()).hexdigest()
            out_rel = sha_to_out.get(sha)
            if c["expect_quarantine"]:
                quarantined_ok = out_rel is None
                per_cat[c["category"]] = {
                    "pii_total": len(c["pii"]),
                    "pii_removed": len(c["pii"]) if quarantined_ok else 0,
                    "pii_leaked": 0 if quarantined_ok else len(c["pii"]),
                    "false_positives": 0,
                    "quarantined_ok": quarantined_ok,
                }
                continue

            file_text = ""
            if out_rel:
                p = out_dir / out_rel
                if p.is_file():
                    file_text = _norm(out_rel + "\n" + p.read_text(encoding="utf-8", errors="ignore"))
            leaked = [x for x in c["pii"] if _norm(x) in file_text]
            fp = [x for x in c["preserve"] if _norm(x) not in file_text]
            tp = len(c["pii"]) - len(leaked)
            per_cat[c["category"]] = {
                "pii_total": len(c["pii"]),
                "pii_removed": tp,
                "pii_leaked": leaked,
                "false_positives": fp,
                "precision": tp / (tp + len(fp)) if (tp + len(fp)) else 1.0,
                "recall": tp / len(c["pii"]) if c["pii"] else 1.0,
            }
        return {"runtime_secs": round(rt, 3), "contract": contract, "categories": per_cat}


def eval_identity_stress() -> Dict[str, Any]:
    """Phase 4: Identity linking stress test with 8 trap scenarios."""
    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        in_dir = tmp_path / "id_in"
        out_dir = tmp_path / "id_out"
        in_dir.mkdir(parents=True, exist_ok=True)

        # Ground truth patient IDs:
        # P1: Kavita Deshmukh (English CSV + Devanagari JSON + different hospital phone match)
        # P2: Kavita Deshmukh (homonym! different DOB + different phone -> MUST NOT merge with P1)
        # P3: Rajesh Kumar Verma / R. K. Verma (initials + expanded + shared phone)
        # P4: Rajesh Kumar Verma (conflicting DOB + phone -> MUST NOT merge with P3)
        # P5: Sunita Devi (incomplete identifier, name+DOB match across hospitals)
        # P6: Anita Devi (similar family name, different person)
        docs = {
            "p1_hosp_a.json": ({"patient_name": "Kavita Deshmukh", "dob": "1977-04-12", "phone": "9823456712", "hospital": "Apex"}, "P1"),
            "p1_hosp_b.json": ({"naam": "कविता देशमुख", "phone": "+91 9823456712", "hospital": "Metro"}, "P1"),
            "p2_homonym.json": ({"patient_name": "Kavita Deshmukh", "dob": "1992-11-03", "phone": "9811998877", "hospital": "Apex"}, "P2"),
            "p3_expanded.json": ({"patient_name": "Rajesh Kumar Verma", "phone": "9415099881", "dob": "1980-01-15"}, "P3"),
            "p3_initials.json": ({"patient_name": "R. K. Verma", "phone": "9415099881", "dob": "1980-01-15"}, "P3"),
            "p4_conflict.json": ({"patient_name": "Rajesh Kumar Verma", "phone": "9988112233", "dob": "1964-09-20"}, "P4"),
            "p5_hosp_a.json": ({"patient_name": "Sunita Devi", "dob": "1985-06-10", "mrn": "H1-0091"}, "P5"),
            "p5_hosp_b.json": ({"patient_name": "Sunita Devi", "dob": "1985-06-10", "mrn": "H2-4410"}, "P5"),
            "p6_similar_fam.json": ({"patient_name": "Anita Devi", "dob": "1985-06-10", "mrn": "H2-4419"}, "P6"),
        }
        import hashlib
        sha_true = {}
        for fname, (obj, true_p) in docs.items():
            p = in_dir / fname
            raw = json.dumps(obj, ensure_ascii=False).encode("utf-8")
            p.write_bytes(raw)
            sha_true[hashlib.sha256(raw).hexdigest()] = true_p

        rt, report, recs, _ = _run_engine(in_dir, out_dir, secret="m25-id-stress")
        out_to_true = {}
        for e in report.get("files", []):
            if e.get("output"):
                out_to_true[e["output"]] = sha_true.get(e["input_sha256"])

        units = []
        for r in recs:
            tp = out_to_true.get(r["file"])
            if tp:
                units.append((tp, r.get("patient")))

        tp_pairs = fp_pairs = fn_pairs = 0
        for i in range(len(units)):
            for j in range(i + 1, len(units)):
                same_true = units[i][0] == units[j][0]
                same_pred = (units[i][1] is not None) and (units[i][1] == units[j][1])
                if same_true and same_pred:
                    tp_pairs += 1
                elif not same_true and same_pred:
                    fp_pairs += 1
                elif same_true and not same_pred:
                    fn_pairs += 1

        prec = tp_pairs / (tp_pairs + fp_pairs) if (tp_pairs + fp_pairs) else 1.0
        rec = tp_pairs / (tp_pairs + fn_pairs) if (tp_pairs + fn_pairs) else 1.0
        f05 = (1.25 * prec * rec) / (0.25 * prec + rec) if (0.25 * prec + rec) else 0.0

        # Cluster purity
        clusters: Dict[str, List[str]] = defaultdict(list)
        for true_p, pred_p in units:
            clusters[str(pred_p)].append(true_p)
        correct_in_clusters = sum(max(v.count(x) for x in set(v)) for v in clusters.values())
        purity = correct_in_clusters / len(units) if units else 1.0

        return {
            "units": len(units),
            "tp_pairs": tp_pairs,
            "fp_false_merges": fp_pairs,
            "fn_missed_links": fn_pairs,
            "pairwise_precision": prec,
            "pairwise_recall": rec,
            "f0_5": f05,
            "cluster_purity": purity,
            "assignments": units,
        }


def eval_clinical_1000() -> Dict[str, Any]:
    """Phase 5: 1,000+ synthetic clinical values & PII-resembling clinical contexts."""
    items = []
    # Build 1,040 distinct clinical assertions across meds, vitals, labs, ranges, eponyms, codes
    meds = ["Metformin 500 mg BD", "Amlodipine 5 mg OD", "Atorvastatin 20 mg HS", "Pantoprazole 40 mg OD", "Azithromycin 500 mg OD"]
    labs = ["HbA1c 7.4%", "Creatinine 1.0 mg/dL", "Hemoglobin 12.8 g/dL", "WBC 11400 /uL", "Platelets 185000 /uL", "TSH 3.8 mIU/L"]
    vitals = ["BP 124/80 mmHg", "Pulse 76 bpm", "Temp 38.2 C", "SpO2 98%", "RR 18 /min"]
    diags = ["Parkinson's disease", "Addison's disease", "Alzheimer's disease", "Graves' disease", "Hodgkin's lymphoma", "Type 2 Diabetes (ICD-10 E11.9)"]
    ranges = ["Ref 70-110 mg/dL", "Ref 3.5-5.1 mEq/L", "Ref 4000-11000 /uL"]

    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        in_dir = tmp_path / "clin_in"
        out_dir = tmp_path / "clin_out"
        in_dir.mkdir(parents=True, exist_ok=True)
        for idx in range(200):
            m = meds[idx % len(meds)]
            l = labs[idx % len(labs)]
            v = vitals[idx % len(vitals)]
            d = diags[idx % len(diags)]
            r = ranges[idx % len(ranges)]
            txt = f"Patient: Dummy Person {idx}\nDx: {d}\nRx: {m}\nLab: {l} ({r})\nVital: {v}\n"
            (in_dir / f"clin_{idx:03d}.txt").write_text(txt, encoding="utf-8")
            items.extend([d, m, l, r, v])  # 5 * 200 = 1,000 clinical values

        rt, _, _, _ = _run_engine(in_dir, out_dir, secret="m25-clin-1000")
        all_norm, _ = _collect_san_text_and_paths(out_dir)
        preserved = 0
        changed = []
        for val in items:
            if _norm(val) in all_norm:
                preserved += 1
            else:
                if len(changed) < 20:
                    changed.append(val)
        return {
            "total_clinical_values": len(items),
            "preserved": preserved,
            "changed_count": len(items) - preserved,
            "preservation_pct": (preserved / len(items)) * 100.0,
            "changed_examples": changed,
            "runtime_secs": round(rt, 3),
        }


def eval_filename_privacy() -> Dict[str, Any]:
    """Phase 6: Filename, directory, and report/log exposure test."""
    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        in_dir = tmp_path / "fn_in"
        out_dir = tmp_path / "fn_out"

        test_files = [
            ("Discharge_Summary_Reena_Nishad_JJH-0076928.txt", "Patient: Reena Nishad\nMRN: JJH-0076928\nBP 120/80 mmHg"),
            ("sanjeevani_ds_IPD-2026-00432.txt", "Patient: Kavita Nair\nMRN: IPD-2026-00432\nHbA1c 7.1%"),
            ("jeevanjyoti_ds_IP-26-00134.txt", "Patient: Sunil Mishra\nMRN: IP-26-00134\nTemp 37.0 C"),
            ("dhhardoi_ds_DHH-IPD-00591.txt", "Patient: Fatima Bano\nMRN: DHH-IPD-00591\nSpO2 99%"),
            ("7585697553_report_0010.json", json.dumps({"phone": "7585697553", "hb": "13.2 g/dL"})),
            ("Rohan_Verma/Ward_A/कविता_देशमुख_note.txt", "Patient: Rohan Verma\nBP 118/78 mmHg"),
            ("dup_dir/Priya_Sharma_dup.txt", "Patient: Priya Sharma\nPulse 72 bpm"),
            ("dup_dir_2/Priya_Sharma_dup.txt", "Patient: Priya Sharma\nPulse 72 bpm"),
        ]
        sensitive_tokens = [
            "Reena_Nishad", "Reena", "Nishad", "JJH-0076928",
            "IPD-2026-00432", "IP-26-00134", "DHH-IPD-00591",
            "7585697553", "Rohan_Verma", "कविता_देशमुख", "Priya_Sharma",
        ]
        for rel, body in test_files:
            p = in_dir / rel
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text(body, encoding="utf-8")

        rt, report, recs, contract = _run_engine(in_dir, out_dir, secret="m25-fn-priv")
        _, san_paths = _collect_san_text_and_paths(out_dir)
        joined_paths = _norm("\n".join(san_paths))
        report_txt = _norm((out_dir / "report.json").read_text(encoding="utf-8"))
        records_txt = _norm((out_dir / "records.jsonl").read_text(encoding="utf-8"))

        path_leaks = [tok for tok in sensitive_tokens if _norm(tok) in joined_paths]
        report_leaks = [tok for tok in sensitive_tokens if _norm(tok) in report_txt]
        records_leaks = [tok for tok in sensitive_tokens if _norm(tok) in records_txt]

        return {
            "files_tested": len(test_files),
            "sanitized_paths": san_paths,
            "path_leaks": path_leaks,
            "report_leaks": report_leaks,
            "records_leaks": records_leaks,
            "contract": contract,
        }


def eval_reidentification_attack() -> Dict[str, Any]:
    """Phase 7: Quasi-identifier linkage attack before vs after sanitisation."""
    # Independent 20-patient synthetic attacker table with unique QI combinations:
    # (age, admit_date, diagnosis, city, profession)
    import random
    rng = random.Random(202607)
    rare_diags = ["Wilson's disease", "Guillain-Barre syndrome", "Takayasu arteritis", "Myasthenia gravis", "Addison's disease"]
    profs = ["School Principal", "Airline Pilot", "District Judge", "Classical Violinist", "Marine Engineer"]
    cities = ["Pune", "Lucknow", "Jaipur", "Kochi", "Chandigarh"]

    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        in_dir = tmp_path / "reid_in"
        out_dir = tmp_path / "reid_out"
        in_dir.mkdir(parents=True, exist_ok=True)

        truth_rows = []
        for idx in range(20):
            age = 31 + idx * 2
            admit = f"2026-03-{10 + (idx % 18):02d}"
            diag = rare_diags[idx % len(rare_diags)]
            prof = profs[(idx // 2) % len(profs)]
            city = cities[(idx // 4) % len(cities)]
            name = f"Target Person{idx}"
            txt = (
                f"Patient Name: {name}\n"
                f"Age: {age} years\n"
                f"Admission Date: {admit}\n"
                f"City: {city}\n"
                f"Occupation: {prof}\n"
                f"Diagnosis: {diag}\n"
            )
            (in_dir / f"reid_{idx:02d}.txt").write_text(txt, encoding="utf-8")
            truth_rows.append({"idx": idx, "age": str(age), "admit": admit, "diag": diag, "prof": prof, "city": city})

        # Before sanitisation: exact QI tuple (age, admit, diag, city, prof) uniquely identifies 20/20
        before_unique = 20
        _run_engine(in_dir, out_dir, secret="m25-reid")
        san_files = list((out_dir / "sanitized").rglob("*.txt"))
        after_exact_qi_matches = 0
        for p in san_files:
            t = _norm(p.read_text(encoding="utf-8", errors="ignore"))
            for row in truth_rows:
                # Attacker tries exact (age + admit_date + city + rare_diag) match
                if _norm(row["age"]) in t and _norm(row["admit"]) in t and _norm(row["diag"]) in t:
                    after_exact_qi_matches += 1
                    break

        return {
            "attacker_records": len(truth_rows),
            "before_sanitisation_unique_links": before_unique,
            "before_attack_success_rate": 1.0,
            "after_exact_qi_links": after_exact_qi_matches,
            "after_attack_success_rate": after_exact_qi_matches / len(truth_rows),
        }


def main() -> None:
    results = {
        "large_dev_gen": eval_large_split("dev_gen", seed=202601),
        "large_held_out": eval_large_split("held_out", seed=202602),
        "adversarial_15": eval_adversarial_15(),
        "identity_stress": eval_identity_stress(),
        "clinical_1000": eval_clinical_1000(),
        "filename_privacy": eval_filename_privacy(),
        "reidentification_attack": eval_reidentification_attack(),
    }
    print(json.dumps(results, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
