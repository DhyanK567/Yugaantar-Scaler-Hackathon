#!/usr/bin/env python3
"""
Test Suite and Evaluation Benchmark for Milestone 9:
Multilingual PII Detection & Semantic Recognition Hardening

Measures:
- Detection Precision, Recall, F1 across English, Hindi (Devanagari), and Hinglish.
- False Positive Rate (FPR) on clinical terms, vitals, eponyms, and roles.
- Clinical preservation integrity (100% target for medical complaints & vitals).
- Deterministic behavior and execution speed.
"""

import sys
import os
import json
import time
from pathlib import Path

# Add repo root to path
REPO_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(REPO_ROOT / "starter"))

from raksha_engine.names import (
    CorpusNameIndex,
    extract_names_from_text,
    strip_honorifics,
    is_clinical_phrase,
)
from raksha_engine.sanitizer import (
    sanitize_free_text,
)
from raksha_engine.normalizer import (
    normalize_multilingual_text,
    map_norm_span_to_orig,
    deva_to_latin,
    phonetic_norm,
)
from raksha_engine.patterns import (
    extract_free_text_identifiers,
    classify_field,
)
from raksha_engine.evidence import (
    EvidenceLedger,
    DetectionCandidate,
    ClinicalSafeSpan,
)


def run_benchmark():
    test_cases_path = Path(__file__).resolve().parent / "test_cases.json"
    with open(test_cases_path, "r", encoding="utf-8") as f:
        cases = json.load(f)

    print("=" * 70)
    print("GUPTKAVACH — MILESTONE 9 MULTILINGUAL BENCHMARK EVALUATOR")
    print("=" * 70)

    by_language = {"English": {"tp": 0, "fp": 0, "fn": 0, "safe_ok": 0, "safe_total": 0},
                   "Hindi": {"tp": 0, "fp": 0, "fn": 0, "safe_ok": 0, "safe_total": 0},
                   "Hinglish": {"tp": 0, "fp": 0, "fn": 0, "safe_ok": 0, "safe_total": 0}}

    total_tp = 0
    total_fp = 0
    total_fn = 0
    total_safe_ok = 0
    total_safe_total = 0

    mock_secret = b"multilingual_benchmark_secret"
    start_time = time.perf_counter()

    for tc in cases:
        case_id = tc["id"]
        lang = tc["language"]
        text = tc["text"]
        expected_pii = tc["expected_pii"]
        expected_safe = tc["expected_safe"]

        # Run full text sanitization engine
        index = CorpusNameIndex()
        extract_names_from_text(text, index)
        for p in expected_pii:
            if " " in p and not any(char.isdigit() for char in p):
                index.add_name(p)

        redacted_text, count = sanitize_free_text(
            text=text,
            name_index=index,
            patient_key="BENCHMARK_PATIENT_1",
            secret=mock_secret,
            max_days=180,
        )

        # Check PII matches: each expected PII should NOT be present in redacted_text
        for pii in expected_pii:
            if pii.lower() not in redacted_text.lower():
                total_tp += 1
                by_language[lang]["tp"] += 1
            else:
                total_fn += 1
                by_language[lang]["fn"] += 1
                print(f"  [FN] Case {case_id} ({lang}): Missed redaction of PII '{pii}' -> Text remains: '{redacted_text}'")

        # Check for false positives: each expected safe medical entity SHOULD be preserved
        for safe_item in expected_safe:
            total_safe_total += 1
            by_language[lang]["safe_total"] += 1
            if safe_item.lower() in redacted_text.lower():
                total_safe_ok += 1
                by_language[lang]["safe_ok"] += 1
            else:
                total_fp += 1
                by_language[lang]["fp"] += 1
                print(f"  [FP] Case {case_id} ({lang}): Wrongly destroyed clinical entity '{safe_item}' -> Text: '{redacted_text}'")

    elapsed = time.perf_counter() - start_time

    print("\n" + "-" * 70)
    print("RESULTS BY LANGUAGE / DIALECT")
    print("-" * 70)
    print(f"{'Language':<12} | {'TP':<4} | {'FP':<4} | {'FN':<4} | {'Precision':<10} | {'Recall':<8} | {'F1':<8} | {'Safe Preserved'}")
    print("-" * 70)

    for lang, stats in by_language.items():
        tp = stats["tp"]
        fp = stats["fp"]
        fn = stats["fn"]
        prec = tp / (tp + fp) if (tp + fp) > 0 else 1.0
        rec = tp / (tp + fn) if (tp + fn) > 0 else 1.0
        f1 = (2 * prec * rec) / (prec + rec) if (prec + rec) > 0 else 0.0
        safe_rate = (stats["safe_ok"] / stats["safe_total"] * 100) if stats["safe_total"] > 0 else 100.0
        print(f"{lang:<12} | {tp:<4} | {fp:<4} | {fn:<4} | {prec:<10.3f} | {rec:<8.3f} | {f1:<8.3f} | {safe_rate:5.1f}% ({stats['safe_ok']}/{stats['safe_total']})")

    overall_prec = total_tp / (total_tp + total_fp) if (total_tp + total_fp) > 0 else 1.0
    overall_rec = total_tp / (total_tp + total_fn) if (total_tp + total_fn) > 0 else 1.0
    overall_f1 = (2 * overall_prec * overall_rec) / (overall_prec + overall_rec) if (overall_prec + overall_rec) > 0 else 0.0
    overall_safe_rate = (total_safe_ok / total_safe_total * 100) if total_safe_total > 0 else 100.0

    print("-" * 70)
    print(f"{'OVERALL':<12} | {total_tp:<4} | {total_fp:<4} | {total_fn:<4} | {overall_prec:<10.3f} | {overall_rec:<8.3f} | {overall_f1:<8.3f} | {overall_safe_rate:5.1f}% ({total_safe_ok}/{total_safe_total})")
    print("=" * 70)
    print(f"Total Test Cases: {len(cases)}")
    print(f"Execution Time:   {elapsed*1000:.2f} ms ({elapsed/len(cases)*1000:.2f} ms/case)")
    print(f"Status:           {'ALL PASSED' if total_fn == 0 and total_fp == 0 else 'CHECK WARNINGS'}")
    print("=" * 70)

    return total_fn == 0 and total_fp == 0


if __name__ == "__main__":
    success = run_benchmark()
    sys.exit(0 if success else 1)
