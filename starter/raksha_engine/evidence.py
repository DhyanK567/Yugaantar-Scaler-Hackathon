"""Deterministic Evidence Model & Semantic Conflict Resolution Engine.
Implements:
- Structured DetectionCandidate representation
- Priority-driven overlap resolution
- Explicit conflict-resolution between PII evidence and clinical preservation evidence
- Protection for medical eponyms, clinical complaints (C/O fever vs C/O Ramesh),
  worker roles (ASHA worker vs Asha Rajput), and medical measurements (BP, dosages).
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import List, Optional, Set, Tuple


@dataclass
class DetectionCandidate:
    candidate_type: str
    orig_start: int
    orig_end: int
    matched_text: str
    detection_source: str
    context_evidence: str
    priority: int = 50
    confidence: float = 1.0
    final_action: str = "REDACT"
    reason_code: str = "CONFIRMED_PII"

    def overlaps_with(self, other: DetectionCandidate) -> bool:
        return max(self.orig_start, other.orig_start) < min(self.orig_end, other.orig_end)


@dataclass
class ClinicalSafeSpan:
    span_type: str  # EPONYM, COMPLAINT, ROLE, VITAL, MEDICATION, DOCTOR
    start: int
    end: int
    text: str
    reason: str


# ---------------------------------------------------------------------------
# Clinical Preservation Gazetteers & Regex Patterns
# ---------------------------------------------------------------------------

# Disease eponyms that contain person-like names
RX_CLINICAL_EPONYMS = re.compile(
    r"(?i)\b("
    r"parkinson(?:'s)?(?:\s+disease|\s+syndrome)?"
    r"|alzheimer(?:'s)?(?:\s+disease|\s+syndrome)?"
    r"|bell(?:'s)?\s+palsy"
    r"|crohn(?:'s)?(?:\s+disease)?"
    r"|addison(?:'s)?(?:\s+disease)?"
    r"|hodgkin(?:'s)?(?:\s+lymphoma)?"
    r"|graves'(?:\s+disease)?"
    r"|cushing(?:'s)?(?:\s+syndrome|\s+disease)?"
    r"|guillain[- ]barre(?:\s+syndrome)?"
    r"|kawasaki(?:\s+disease)?"
    r"|meniere(?:'s)?(?:\s+disease)?"
    r"|down(?:'s)?\s+syndrome"
    r"|turner(?:'s)?\s+syndrome"
    r"|wilson(?:'s)?\s+disease"
    r"|hansens?(?:\s+disease)?"
    r"|paget(?:'s)?\s+disease"
    r"|raynaud(?:'s)?\s+phenomenon"
    r")\b"
)

# Clinical complaints: "C/O fever", "C/O cough", "c/o chest pain" (NOT "C/O Ramesh")
RX_CLINICAL_COMPLAINT = re.compile(
    r"(?i)\b(?:C/O|c/o|C\.O\.|Complaining\s+of|Complain\s+of|शिकायत)\s*[:\-]?\s*"
    r"(?P<complaint>[A-Za-z\u0900-\u097f\s]{2,40}?)"
    r"(?=\s*(?:,|\n|;|\.|\bfor\b|\bsince\b|\bfrom\b|\bBP\b|\bPulse\b|\bPR\b|\d+\s*(?:days?|din|दिन)|$))"
)

# Common symptoms list for C/O validation
CLINICAL_SYMPTOMS = {
    "fever", "bukhar", "cough", "khansi", "cold", "pain", "chest pain", "abdomen pain",
    "abdominal pain", "headache", "vomiting", "ulti", "weakness", "kamjori", "loose stools",
    "diarrhea", "dyspnea", "shortness of breath", "breathlessness", "burning micturition",
    "bleeding", "chills", "dizziness", "rash", "swelling", "nausea", "loss of appetite",
    "बुखार", "खांसी", "दर्द", "पेट दर्द", "उल्टी", "कमजोरी", "दस्त", "सिरदर्द",
}

# Health worker roles: "ASHA worker", "Anganwadi worker", "duty nurse"
RX_WORKER_ROLES = re.compile(
    r"(?i)\b("
    r"(?:ASHA|Asha)\s+worker"
    r"|Anganwadi\s+(?:worker|helper|sewika)"
    r"|ANM(?:\s+worker)?"
    r"|Staff\s+nurse"
    r"|Duty\s+(?:nurse|doctor|officer)"
    r"|Ward\s+boy"
    r"|आशा\s*कार्यकर्ता"
    r"|आंगनवाड़ी\s*कार्यकर्ता"
    r")\b"
)

# Family medical history (e.g. "Family history of diabetes")
RX_FAMILY_HISTORY = re.compile(
    r"(?i)\b(?:no\s+)?family\s+history\s+of\s+[A-Za-z\s]{3,35}\b"
)

# Doctor / Physician mentions (to avoid redacting doctors as patients)
RX_DOCTOR_MENTION = re.compile(
    r"(?i)\b(?:Dr\.?|Doctor|डॉक्टर|डॉ\.)\s+[A-Za-z\u0900-\u097f][A-Za-z\u0900-\u097f.\s]{2,35}\b"
)

# Medical vitals & measurements (BP 120/80, Pulse 72/min, Dolo 650 mg)
RX_VITALS_AND_DOSES = re.compile(
    r"(?i)(?:"
    r"\bBP\s*[:\-]?\s*\d{2,3}[/-]\d{2,3}\b"
    r"|\bPulse\s*[:\-]?\s*\d{2,3}(?:\s*/\s*min)?\b"
    r"|\bSpO2\s*[:\-]?\s*\d{2,3}\s*%\b"
    r"|\bTemp(?:erature)?\s*[:\-]?\s*\d{2,3}(?:\.\d)?\s*(?:F|C)\b"
    r"|\b(?:Dolo|Paracetamol|Azithromycin|Amoxicillin|Metformin|Amlodipine|Pantoprazole|Ceftriaxone)\s+\d{2,4}\s*(?:mg|g|ml)\b"
    r"|\b\d{1,4}\s*(?:mg|mcg|ml|IU|units|tab|cap)\b"
    r"|\b[01]-[01]-[01]\b"
    r"|\b(?:OD|BD|TDS|QID|HS|SOS)\b"
    r")"
)


class EvidenceLedger:
    """Collects detection candidates and clinical preservation spans,
    resolving overlaps and contextual conflicts deterministically.
    """

    def __init__(self, raw_text: str):
        self.raw_text = raw_text
        self.candidates: list[DetectionCandidate] = []
        self.clinical_spans: list[ClinicalSafeSpan] = []
        self._extract_clinical_safe_spans()

    def _extract_clinical_safe_spans(self) -> None:
        """Scan text for clinical entities that must never be redacted."""
        text = self.raw_text

        # 1. Eponymic diagnoses
        for m in RX_CLINICAL_EPONYMS.finditer(text):
            self.clinical_spans.append(
                ClinicalSafeSpan("EPONYM", m.start(), m.end(), m.group(0), "Eponymic Medical Diagnosis")
            )

        # 2. Clinical complaints ("C/O fever" vs "C/O Ramesh")
        for m in RX_CLINICAL_COMPLAINT.finditer(text):
            complaint_val = m.group("complaint").strip().lower()
            # If complaint value matches symptoms or is not a proper 2-3 word name
            if complaint_val in CLINICAL_SYMPTOMS or any(s in complaint_val for s in ("fever", "pain", "cough", "cold", "vomiting")):
                self.clinical_spans.append(
                    ClinicalSafeSpan("COMPLAINT", m.start(), m.end(), m.group(0), "Clinical Chief Complaint")
                )

        # 3. Health worker roles ("ASHA worker")
        for m in RX_WORKER_ROLES.finditer(text):
            self.clinical_spans.append(
                ClinicalSafeSpan("ROLE", m.start(), m.end(), m.group(0), "Healthcare Worker Role")
            )

        # 4. Family medical history
        for m in RX_FAMILY_HISTORY.finditer(text):
            self.clinical_spans.append(
                ClinicalSafeSpan("FAMILY_HISTORY", m.start(), m.end(), m.group(0), "Family Medical History Context")
            )

        # 5. Doctor / Physician mentions
        for m in RX_DOCTOR_MENTION.finditer(text):
            self.clinical_spans.append(
                ClinicalSafeSpan("DOCTOR", m.start(), m.end(), m.group(0), "Practitioner Identity")
            )

        # 6. Vitals and dosages
        for m in RX_VITALS_AND_DOSES.finditer(text):
            self.clinical_spans.append(
                ClinicalSafeSpan("VITAL_OR_DOSE", m.start(), m.end(), m.group(0), "Medical Vital/Measurement")
            )

    def add_candidate(self, candidate: DetectionCandidate) -> None:
        self.candidates.append(candidate)

    def resolve_conflicts(self) -> list[DetectionCandidate]:
        """Apply deterministic conflict-resolution rules.
        Returns a non-overlapping, sorted list of verified redaction candidates.
        """
        verified: list[DetectionCandidate] = []

        # Step 1: Discard or alter candidates that conflict with clinical safe spans
        for cand in self.candidates:
            has_clinical_conflict = False
            for c_span in self.clinical_spans:
                # Check overlap
                if max(cand.orig_start, c_span.start) < min(cand.orig_end, c_span.end):
                    has_clinical_conflict = True
                    # Exception: Strong direct IDs (Aadhaar 12-digits, phone 10-digits) inside doctor notes
                    # are still PII, unless part of a vital/dose
                    if c_span.span_type == "VITAL_OR_DOSE" and cand.candidate_type in ("PIN", "MRN", "PHONE"):
                        cand.final_action = "PRESERVE"
                        cand.reason_code = f"CONFLICT_WITH_{c_span.span_type}"
                    elif c_span.span_type in ("EPONYM", "COMPLAINT", "ROLE", "FAMILY_HISTORY", "DOCTOR"):
                        if cand.candidate_type in ("PATIENT_NAME", "RELATIVE_NAME"):
                            cand.final_action = "PRESERVE"
                            cand.reason_code = f"CONFLICT_WITH_{c_span.span_type}"
                    break

            if cand.final_action == "REDACT":
                verified.append(cand)

        # Step 2: Resolve overlapping PII candidates (Priority sorting)
        # Sort by: orig_start ASC, length DESC, priority DESC
        verified.sort(
            key=lambda c: (c.orig_start, -(c.orig_end - c.orig_start), -c.priority)
        )

        non_overlapping: list[DetectionCandidate] = []
        last_end = -1
        for cand in verified:
            if cand.orig_start >= last_end:
                non_overlapping.append(cand)
                last_end = cand.orig_end
            else:
                # Overlap detected: candidate with higher priority was chosen
                cand.final_action = "OVERLAP_SUPPRESSED"
                cand.reason_code = "SUBORDINATED_BY_HIGHER_PRIORITY"

        return non_overlapping

    def apply_redactions(
        self,
        tag_map: Optional[dict[str, str]] = None,
    ) -> Tuple[str, int, list[DetectionCandidate]]:
        """Apply all resolved redactions to the raw text from right to left.
        Preserves exact Unicode character indexing throughout the transformation.
        """
        resolved = self.resolve_conflicts()
        if not resolved:
            return self.raw_text, 0, []

        default_tag_map = {
            "PATIENT_NAME": "[PATIENT_NAME]",
            "RELATIVE_NAME": "[RELATIVE_NAME]",
            "AADHAAR": "[AADHAAR]",
            "AADHAAR_MASKED": "[AADHAAR_MASKED]",
            "ABHA_NUMBER": "[ABHA_NUMBER]",
            "ABHA_ADDRESS": "[ABHA_ADDRESS]",
            "PHONE": "[PHONE]",
            "PHONE_MASKED": "[PHONE_MASKED]",
            "MRN": "[MRN]",
            "PAN": "[PAN]",
            "INSURANCE_ID": "[INSURANCE_ID]",
            "EMAIL": "[EMAIL]",
            "DOB": "[DOB]",
            "VILLAGE": "[VILLAGE]",
            "HOUSE": "[HOUSE]",
            "LOCALITY": "[LOCALITY]",
            "LANDMARK": "[LANDMARK]",
            "PIN": "[PIN]",
        }
        effective_map = {**default_tag_map, **(tag_map or {})}

        chars = list(self.raw_text)
        count = 0

        # Replace spans from right to left (descending start index)
        for cand in sorted(resolved, key=lambda c: c.orig_start, reverse=True):
            tag = effective_map.get(cand.candidate_type, f"[{cand.candidate_type}]")
            chars[cand.orig_start : cand.orig_end] = list(tag)
            count += 1

        return "".join(chars), count, resolved
