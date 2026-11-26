#!/usr/bin/env python3
"""Phase 3 — Multilingual Contextual PII Intelligence & Conflict Resolution Suite.
Measures Precision, Recall, F1, FP, FN, per-language metrics, and clinical-term FPR.
"""

import sys
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(REPO_ROOT / "starter"))

from raksha_engine.names import CorpusNameIndex, extract_names_from_text
from raksha_engine.sanitizer import sanitize_free_text


CASES = [
    # Contextual disambiguation & conflict resolution
    {"id": "ctx_asha_person", "lang": "English", "text": "Patient: Asha Rajput, age 32 F, C/O fever.", "pii": ["Asha Rajput"], "safe": ["C/O fever"]},
    {"id": "ctx_asha_role", "lang": "English", "text": "ASHA worker conducted pulse polio follow-up at PHC.", "pii": [], "safe": ["ASHA worker", "PHC"]},
    {"id": "ctx_dr_ramesh", "lang": "English", "text": "Reviewed by Dr. Ramesh Kulkarni. Tab Dolo 650 mg TDS.", "pii": [], "safe": ["Dr. Ramesh", "Dolo 650 mg"]},
    {"id": "ctx_co_rel", "lang": "English", "text": "Attendant: Meena Devi C/O Ramesh Chandra, phone 9876543210.", "pii": ["Meena Devi", "Ramesh Chandra", "9876543210"], "safe": []},
    {"id": "ctx_parkinson", "lang": "English", "text": "Diagnosis: Parkinson's disease and Bell's palsy.", "pii": [], "safe": ["Parkinson's disease", "Bell's palsy"]},
    {"id": "ctx_initials", "lang": "English", "text": "Patient: K. V. Ramanathan, ABHA: 12-3456-7890-1234.", "pii": ["K. V. Ramanathan", "12-3456-7890-1234"], "safe": []},
    # Hindi (Devanagari)
    {"id": "hi_1", "lang": "Hindi", "text": "मरीज: सुनीता देवी, पिता: मोहन लाल, आधार: 9876 5432 1098, तेज बुखार।", "pii": ["सुनीता देवी", "मोहन लाल", "9876 5432 1098"], "safe": ["तेज बुखार"]},
    {"id": "hi_2", "lang": "Hindi", "text": "रोगी का नाम: राजेश शर्मा, मोबाइल: 9811223344, खांसी और दर्द।", "pii": ["राजेश शर्मा", "9811223344"], "safe": ["खांसी"]},
    # Hinglish
    {"id": "hg_1", "lang": "Hinglish", "text": "Mareez: Pooja Kumari, pita ka naam Suresh Verma, bukhar 2 din se.", "pii": ["Pooja Kumari", "Suresh Verma"], "safe": ["bukhar"]},
    {"id": "hg_2", "lang": "Hinglish", "text": "Attendant: Vikram Singh, pati of Kavita Devi, Tab Paracetamol 500 mg.", "pii": ["Vikram Singh", "Kavita Devi"], "safe": ["Paracetamol 500 mg"]},
]


class TestMultilingualContextualIntelligence(unittest.TestCase):
    def test_contextual_metrics_and_clinical_fpr(self):
        secret = b"m15_5_multilingual_test_secret"
        by_lang = {}
        clinical_total = 0
        clinical_fp = 0

        for c in CASES:
            lang = c["lang"]
            st = by_lang.setdefault(lang, {"tp": 0, "fp": 0, "fn": 0})
            idx = CorpusNameIndex()
            extract_names_from_text(c["text"], idx)
            out, _ = sanitize_free_text(c["text"], idx, "PT-TEST", secret, 180)

            for p in c["pii"]:
                if p.lower() not in out.lower():
                    st["tp"] += 1
                else:
                    st["fn"] += 1
                    self.fail(f"[{c['id']}] Missed PII '{p}' in output: {out}")

            for s in c["safe"]:
                clinical_total += 1
                if s.lower() not in out.lower():
                    st["fp"] += 1
                    clinical_fp += 1
                    self.fail(f"[{c['id']}] False positive removed clinical term '{s}' in output: {out}")

        total_tp = sum(v["tp"] for v in by_lang.values())
        total_fp = sum(v["fp"] for v in by_lang.values())
        total_fn = sum(v["fn"] for v in by_lang.values())
        prec = total_tp / max(1, total_tp + total_fp)
        rec = total_tp / max(1, total_tp + total_fn)
        f1 = 2 * prec * rec / max(1e-9, prec + rec)
        clin_fpr = clinical_fp / max(1, clinical_total)

        self.assertEqual(prec, 1.0)
        self.assertEqual(rec, 1.0)
        self.assertEqual(f1, 1.0)
        self.assertEqual(clin_fpr, 0.0)


if __name__ == "__main__":
    unittest.main()
