#!/usr/bin/env python3
"""
Unit tests for Milestone 9 multilingual components.
Can be executed with `pytest` or `python -m unittest`.
"""

import sys
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(REPO_ROOT / "starter"))

from raksha_engine.normalizer import (
    normalize_multilingual_text,
    map_norm_span_to_orig,
    deva_to_latin,
    phonetic_norm,
    strip_honorifics,
)
from raksha_engine.evidence import (
    EvidenceLedger,
    DetectionCandidate,
    ClinicalSafeSpan,
)
from raksha_engine.names import (
    is_clinical_phrase,
    CorpusNameIndex,
    redact_names_in_text,
)


class TestMultilingualNormalizer(unittest.TestCase):
    def test_unicode_nfc_nfkc(self):
        norm_text, offsets = normalize_multilingual_text("र\u093eम")
        self.assertIn("राम", norm_text)
        self.assertGreaterEqual(len(offsets), len(norm_text))

    def test_bidirectional_offset_mapping(self):
        original = "  Patient:   Amit   Kumar  "
        norm_text, offsets = normalize_multilingual_text(original)
        norm_sub = "Amit"
        n_start = norm_text.find(norm_sub)
        n_end = n_start + len(norm_sub)
        o_start, o_end = map_norm_span_to_orig(offsets, n_start, n_end, len(original))
        self.assertEqual(original[o_start:o_end], "Amit")

    def test_devanagari_transliteration(self):
        deva = "राजेश"
        latin = deva_to_latin(deva)
        self.assertTrue(any(x in latin for x in ["raj", "rajesh", "rajas"]))

    def test_phonetic_normalization(self):
        p1 = phonetic_norm("Shyam")
        p2 = phonetic_norm("Syam")
        self.assertEqual(p1, p2)

    def test_honorific_stripping(self):
        cleaned = strip_honorifics("Smt. Sunita Devi")
        self.assertEqual(cleaned, "Sunita Devi")

        cleaned2 = strip_honorifics("Ramesh ji")
        self.assertEqual(cleaned2, "Ramesh")


class TestSemanticDisambiguation(unittest.TestCase):
    def test_asha_role_vs_person_name(self):
        # Uppercase ASHA role must be preserved
        self.assertTrue(is_clinical_phrase("ASHA"))
        # Titlecase Asha is not a clinical phrase
        self.assertFalse(is_clinical_phrase("Asha"))

    def test_evidence_ledger_conflict_resolution(self):
        text = "Diagnosed with Parkinson's disease."
        ledger = EvidenceLedger(text)
        ledger.add_candidate(DetectionCandidate(
            candidate_type="PATIENT_NAME",
            orig_start=15,
            orig_end=24,
            matched_text="Parkinson",
            detection_source="heuristic",
            context_evidence="Test candidate",
        ))
        resolved = ledger.resolve_conflicts()
        # Parkinson must be rejected because it overlaps with clinical safe span
        self.assertEqual(len(resolved), 0)


if __name__ == "__main__":
    unittest.main()
