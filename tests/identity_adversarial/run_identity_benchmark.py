"""M11.8 Adversarial Identity Resolution Benchmark.

Tests 15 synthetic cross-hospital, multilingual, and false-merge scenarios
against ground truth, reporting per-category TP, FP, FN, Precision, Recall,
F0.5, false merges, abstentions, order invariance, and performance.
"""
from __future__ import annotations

import itertools
import random
import sys
import time
import tracemalloc
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "starter"))

from raksha_engine.linking import RecordClues, resolve_identities, set_name_clue  # noqa: E402
from raksha_engine.privacy import pseudonym  # noqa: E402


def _make_clue(
    rid: str,
    name: str = "",
    strong_ids: set[str] | None = None,
    mrns: set[str] | None = None,
    gender: str = "",
    birth_year: int | None = None,
    age: int | None = None,
    pin: str = "",
    district: str = "",
    village: str = "",
    hospital: str = "",
) -> RecordClues:
    c = RecordClues(
        record_id=rid,
        strong_ids=set(strong_ids or ()),
        mrns=set(mrns or ()),
        gender=gender,
        birth_year=birth_year,
        age=age,
        pin=pin,
        district=district,
        village=village,
    )
    if hasattr(c, "hospital"):
        c.hospital = hospital
    if name:
        set_name_clue(c, name)
    return c


def build_benchmark_cases() -> tuple[list[RecordClues], dict[str, str], dict[str, list[str]]]:
    """Return (clues, true_patient_per_rid, category_rids)."""
    clues: list[RecordClues] = []
    truth: dict[str, str] = {}
    cats: dict[str, list[str]] = {
        "strong_id": [],
        "cross_hospital": [],
        "multilingual": [],
        "name_supporting": [],
        "false_merge_adversarial": [],
        "uncertain": [],
    }

    def add(cat: str, pid: str, c: RecordClues) -> None:
        clues.append(c)
        truth[c.record_id] = pid
        cats[cat].append(c.record_id)

    # 1. Exact same patient across Hospital A, Hospital B, Lab D (different MRNs, shared ABHA/phone)
    add("cross_hospital", "P01", _make_clue("hA_1", "Rahul Kumar", strong_ids={"abha:91112233445566"}, mrns={"mrn:HA101"}, gender="M", birth_year=1988, district="Lucknow", hospital="HospitalA"))
    add("cross_hospital", "P01", _make_clue("hB_1", "Rahul Kumar", strong_ids={"abha:91112233445566", "phone:9811112222"}, mrns={"mrn:HB202"}, gender="M", birth_year=1988, hospital="HospitalB"))
    add("strong_id", "P01", _make_clue("labD_1", "Rahul K.", strong_ids={"phone:9811112222"}, gender="M", age=38, hospital="LabD"))

    # 2. Hindi + English + Hinglish + Devanagari transliteration variants
    add("multilingual", "P02", _make_clue("ml_1", "राहुल शर्मा", strong_ids={"phone:9822223333"}, gender="M", birth_year=1990, district="Kanpur", hospital="HospitalA"))
    add("multilingual", "P02", _make_clue("ml_2", "Rahool Sharma", strong_ids={"phone:9822223333"}, gender="M", birth_year=1990, hospital="HospitalC"))
    add("multilingual", "P03", _make_clue("ml_3", "मोहम्मद शाहिद", gender="M", birth_year=1985, village="Mohanganj", district="Rae Bareli", hospital="HospitalA"))
    add("multilingual", "P03", _make_clue("ml_4", "Mohd. Shahid", gender="M", birth_year=1985, village="Mohanganj", district="Rae Bareli", hospital="LabD"))

    # 3. Initials & Surname-first order with corroborated DOB + District
    add("name_supporting", "P04", _make_clue("ns_1", "Rajesh Kumar Verma", gender="M", birth_year=1975, district="Unnao", pin="209801", hospital="HospitalA"))
    add("name_supporting", "P04", _make_clue("ns_2", "Verma, Rajesh K.", gender="M", birth_year=1975, district="Unnao", pin="209801", hospital="HospitalB"))
    add("name_supporting", "P04", _make_clue("ns_3", "R. K. Verma", gender="M", birth_year=1975, district="Unnao", pin="209801", hospital="LabD"))

    # 4. Duplicate records
    add("strong_id", "P05", _make_clue("dup_1", "Anita Devi", strong_ids={"aadhaar:445566778899"}, gender="F", age=45, district="Hardoi", hospital="HospitalA"))
    add("strong_id", "P05", _make_clue("dup_2", "Anita Devi", strong_ids={"aadhaar:445566778899"}, gender="F", age=45, district="Hardoi", hospital="HospitalA"))

    # 5. False-merge adversarial: Common-name collisions (Sunita Devi x2, no strong ID, different/missing DOB)
    add("false_merge_adversarial", "P06", _make_clue("fm_common_1", "Sunita Devi", gender="F", age=28, district="Sitapur", hospital="HospitalA"))
    add("false_merge_adversarial", "P07", _make_clue("fm_common_2", "Sunita Devi", gender="F", age=61, district="Sitapur", hospital="HospitalB"))

    # 6. False-merge adversarial: Same name + same village + similar age (only 1-yr diff, no strong ID, no birth_year)
    add("false_merge_adversarial", "P08", _make_clue("fm_vil_1", "Amit Kumar", gender="M", age=40, village="Rampur", hospital="HospitalA"))
    add("false_merge_adversarial", "P09", _make_clue("fm_vil_2", "Amit Kumar", gender="M", age=41, village="Rampur", hospital="HospitalB"))

    # 7. False-merge adversarial: Shared family phone (parent age 58 vs child age 24)
    add("false_merge_adversarial", "P10", _make_clue("fm_fam_1", "Mahesh Tiwari", strong_ids={"phone:9833334444"}, gender="M", age=58, birth_year=1968, hospital="HospitalA"))
    add("false_merge_adversarial", "P11", _make_clue("fm_fam_2", "Priya Tiwari", strong_ids={"phone:9833334444"}, gender="F", age=24, birth_year=2002, hospital="HospitalB"))

    # 8. False-merge adversarial: Conflicting strong identifiers (different Aadhaar, same name & DOB)
    add("false_merge_adversarial", "P12", _make_clue("fm_cid_1", "Suresh Yadav", strong_ids={"aadhaar:111122223333"}, gender="M", birth_year=1980, district="Barabanki", hospital="HospitalA"))
    add("false_merge_adversarial", "P13", _make_clue("fm_cid_2", "Suresh Yadav", strong_ids={"aadhaar:999988887777"}, gender="M", birth_year=1980, district="Barabanki", hospital="HospitalB"))

    # 9. False-merge adversarial: Transitive chain (A matches B on phone, B matches C on MRN, A conflicts with C on birth_year & Aadhaar)
    add("false_merge_adversarial", "P14", _make_clue("fm_tr_A", "Vikram Singh", strong_ids={"phone:9844445555", "aadhaar:222233334444"}, gender="M", birth_year=1972, hospital="HospitalA"))
    add("false_merge_adversarial", "P14", _make_clue("fm_tr_B", "Vikram Singh", strong_ids={"phone:9844445555"}, mrns={"mrn:HC777"}, gender="M", hospital="HospitalC"))
    add("false_merge_adversarial", "P15", _make_clue("fm_tr_C", "Vikram Singh", strong_ids={"aadhaar:888877776666"}, mrns={"mrn:HC777"}, gender="M", birth_year=1995, hospital="HospitalC"))

    # 10. False-merge adversarial: Hospital-scoped MRN collision (IP-001 at HospitalA vs IP-001 at HospitalB, different people)
    add("false_merge_adversarial", "P16", _make_clue("fm_mrn_A", "Kiran Bala", mrns={"mrn:IP001"}, gender="F", birth_year=1977, hospital="HospitalA"))
    add("false_merge_adversarial", "P17", _make_clue("fm_mrn_B", "Deepak Joshi", mrns={"mrn:IP001"}, gender="M", birth_year=1992, hospital="HospitalB"))

    # 11. False-merge adversarial: Similar phonetic names belonging to different people
    add("false_merge_adversarial", "P18", _make_clue("fm_ph_1", "Ramesh Patel", gender="M", birth_year=1982, district="Unnao", hospital="HospitalA"))
    add("false_merge_adversarial", "P19", _make_clue("fm_ph_2", "Suresh Patel", gender="M", birth_year=1982, district="Unnao", hospital="HospitalB"))

    # 12. Uncertain / missing identifiers
    add("uncertain", "P20", _make_clue("unc_1", "Ramesh", hospital="HospitalA"))
    add("uncertain", "P21", _make_clue("unc_2", "", age=50, gender="M", hospital="LabD"))

    return clues, truth, cats


def score_subset(rids: list[str], res: dict[str, str | None], truth: dict[str, str]) -> dict:
    tp = fp = fn = 0
    for a, b in itertools.combinations(rids, 2):
        same_truth = truth[a] == truth[b]
        pa, pb = res.get(a), res.get(b)
        same_pred = (pa is not None) and (pa == pb)
        if same_pred and same_truth:
            tp += 1
        elif same_pred and not same_truth:
            fp += 1
        elif not same_pred and same_truth:
            fn += 1
    prec = tp / (tp + fp) if (tp + fp) else 1.0
    rec = tp / (tp + fn) if (tp + fn) else 1.0
    f05 = (1.25 * prec * rec / (0.25 * prec + rec)) if (prec + rec) else 0.0
    abstentions = sum(1 for r in rids if res.get(r) is None)
    return {
        "tp": tp, "fp": fp, "fn": fn,
        "precision": round(prec, 3), "recall": round(rec, 3), "f05": round(f05, 3),
        "false_merges": fp, "abstentions": abstentions,
    }


def main() -> int:
    clues, truth, cats = build_benchmark_cases()

    tracemalloc.start()
    t0 = time.monotonic()
    res = resolve_identities(clues)
    elapsed_ms = (time.monotonic() - t0) * 1000
    _, peak_bytes = tracemalloc.get_traced_memory()
    tracemalloc.stop()

    all_rids = [c.record_id for c in clues]
    overall = score_subset(all_rids, res, truth)

    print("=== M11.8 ADVERSARIAL IDENTITY BENCHMARK ===")
    print(f"Total records: {len(clues)} | Time: {elapsed_ms:.2f} ms | Peak mem: {peak_bytes/1024:.1f} KB")
    print(f"OVERALL: {overall}")
    for cat, rids in cats.items():
        print(f"  [{cat}]: {score_subset(rids, res, truth)}")

    # Order-invariance check
    shuffled = list(clues)
    random.Random(42).shuffle(shuffled)
    res_shuf = resolve_identities(shuffled)
    secret = b"m11_test_secret"
    psn_orig = {k: (pseudonym(v, secret) if v else None) for k, v in res.items()}
    psn_shuf = {k: (pseudonym(v, secret) if v else None) for k, v in res_shuf.items()}
    print(f"Order invariance (identical pseudonyms on shuffled input): {psn_orig == psn_shuf}")
    if psn_orig != psn_shuf:
        diffs = [(k, psn_orig[k], psn_shuf[k]) for k in psn_orig if psn_orig[k] != psn_shuf[k]]
        print(f"  Order diffs ({len(diffs)}): {diffs[:5]}")

    # Different-secret unlinkability check
    psn_diff = {k: (pseudonym(v, b"other_secret") if v else None) for k, v in res.items()}
    collisions = sum(1 for k in psn_orig if psn_orig[k] and psn_orig[k] == psn_diff[k])
    print(f"Cross-secret pseudonym collisions: {collisions}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
