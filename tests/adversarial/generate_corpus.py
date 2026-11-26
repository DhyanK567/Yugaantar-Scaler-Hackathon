"""Independent synthetic adversarial benchmark corpus generator for GuptKavach.

Uses completely unseen synthetic names, identifiers, hospitals, and formats.
"""
from __future__ import annotations

import base64
import json
from pathlib import Path


def build_adversarial_corpus(base_dir: Path) -> dict:
    inp = base_dir / "input"
    if inp.exists():
        import shutil
        shutil.rmtree(inp)
    (inp / "registration").mkdir(parents=True)
    (inp / "notes").mkdir(parents=True)
    (inp / "opd").mkdir(parents=True)
    (inp / "fhir").mkdir(parents=True)
    (inp / "misc").mkdir(parents=True)

    # 1. CSV with misleading headers, PII in header, initials, surname-first, phone variants
    csv_content = (
        "Patient_9811223344_Name,Beneficiary,Contact#,Gram/Mohalla,District,PIN,Age,Sex,DOB,Aadhaar,ABHA,PAN,Insurance_ID,MRN\n"
        "\"Verma, Rajesh K.\",Rajesh Kumar Verma,+91 98112 23344,Bhimpur Kalan,Lucknow,226010,52,M,14/08/1974,4512 8899 3344,91-1234-5678-9012,ABCDE1234F,PMJAY-UP-99887766,KMC/26/991122\n"
        "\"K. S. Iyer\",Kavita Subramanian Iyer,098223-34455,Chandni Chowk,Lucknow,226011,47,F,1979-03-22,XXXX XXXX 4321,,FGHIJ5678K,POL/99/11223344,KMC/26/991123\n"
    )
    (inp / "registration" / "unseen_cohort.csv").write_text(csv_content, encoding="utf-8")

    # 2. Hindi + Hinglish + Devanagari digits + Meaning Traps note
    note_1 = (
        "ओपीडी पर्चा - KMC/26/991122\n"
        "नाम: सुनीता कुमारी   आयु: 44 वर्ष   लिंग: महिला\n"
        "ग्राम: रामपुर खुर्द   पिन: 226010\n"
        "मोबाइल: ९८११२२३३४४\n"
        "S/o Ramesh\n"
        "C/O fever and dry cough x 4 days.\n"
        "K/C/O Parkinson's disease.\n"
        "Rx: Dolo 650 BD x 5 days, Ramipril 5 mg 1-0-1.\n"
        "Vitals: BP 120/80, RBS 245 mg/dL, Hb 14.0 g/dL.\n"
        "Dr. Ramesh reviewed the patient.\n"
        "Sunita ji ko aaram hai. CANARY_ALPHA_9911.\n"
    )
    (inp / "notes" / "hindi_meaning_traps.txt").write_text(note_1, encoding="utf-8")

    # 3. Transliteration + Unicode NFKC / zero-width variation + honorifics
    note_2 = (
        "Patient: Ab\u200bdu\u200bl Rah\u200bman\n"
        "अब्दुल रहमान को बुखार है। Rahman sahab ko Dolo 650 diya.\n"
        "Attendant: W/o Nasreen Begum, H.No. 42, near Jama Masjid, 226012.\n"
        "Dr. Meera Nair advised rest.\n"
    )
    (inp / "notes" / "unicode_hinglish_note.txt").write_text(note_2, encoding="utf-8")

    # 4. Nested JSON with metadata source_path, base64 attachment, and canary
    b64_payload = base64.b64encode(
        b"Witnessed by Harish Chandra, mobile 9876501234. CANARY_B64_7722."
    ).decode("ascii")
    opd_json = {
        "_export_meta": {
            "source_path": "D:\\HIS\\exports\\Kavita_Iyer_991123\\opd.json",
            "canary_tag": "CANARY_META_5544",
        },
        "visits": [
            {
                "visit_id": "KMC/26/991123",
                "complaints": "C/O headache",
                "diagnosis": [{"code": "G20", "display": "Parkinson's disease"}],
                "rx": [{"drug": "Ramipril", "strength": "5 mg", "frequency": "1-0-1"}],
                "attachment": {"contentType": "text/plain", "data": b64_payload},
            }
        ],
    }
    (inp / "opd" / "nested_meta.json").write_text(json.dumps(opd_json, indent=2), encoding="utf-8")

    # 5. Filename PII + Canary in filename
    (inp / "notes" / "9876543210_Discharge_Kavita_Iyer_CANARY_FNAME_3311.txt").write_text(
        "Patient: Kavita Iyer\nDiagnosis: Acute bronchitis\nTab Azithromycin 500 mg OD x 3 days\n",
        encoding="utf-8",
    )

    # 6. FHIR R4 Bundle with Patient + RelatedPerson + Practitioner
    fhir_bundle = {
        "resourceType": "Bundle",
        "id": "adv-bundle-001",
        "meta": {"source": "#KMC/26/991122"},
        "type": "document",
        "entry": [
            {
                "fullUrl": "urn:uuid:11111111-1111-4111-8111-111111111111",
                "resource": {
                    "resourceType": "Composition",
                    "id": "11111111-1111-4111-8111-111111111111",
                    "status": "final",
                    "subject": {"reference": "urn:uuid:22222222-2222-4222-8222-222222222222", "display": "Rajesh Kumar Verma"},
                    "author": [{"reference": "urn:uuid:33333333-3333-4333-8333-333333333333", "display": "Dr. Ramesh"}],
                },
            },
            {
                "fullUrl": "urn:uuid:22222222-2222-4222-8222-222222222222",
                "resource": {
                    "resourceType": "Patient",
                    "id": "22222222-2222-4222-8222-222222222222",
                    "identifier": [{"system": "https://kmc.example/mrn", "value": "KMC/26/991122"}],
                    "name": [{"text": "Rajesh Kumar Verma"}],
                    "telecom": [{"system": "phone", "value": "9811223344"}],
                    "gender": "male",
                    "birthDate": "1974-08-14",
                    "address": [{"line": ["H.No. 19"], "district": "Lucknow", "postalCode": "226010"}],
                },
            },
            {
                "fullUrl": "urn:uuid:33333333-3333-4333-8333-333333333333",
                "resource": {
                    "resourceType": "Practitioner",
                    "id": "33333333-3333-4333-8333-333333333333",
                    "name": [{"text": "Dr. Ramesh"}],
                },
            },
            {
                "fullUrl": "urn:uuid:44444444-4444-4444-8444-444444444444",
                "resource": {
                    "resourceType": "RelatedPerson",
                    "id": "44444444-4444-4444-8444-444444444444",
                    "patient": {"reference": "urn:uuid:22222222-2222-4222-8222-222222222222"},
                    "name": [{"text": "Maheshwar Verma"}],
                    "telecom": [{"system": "phone", "value": "9811223300"}],
                },
            },
        ],
    }
    (inp / "fhir" / "adv_bundle.json").write_text(json.dumps(fhir_bundle, indent=2), encoding="utf-8")

    # 7. Malformed / truncated / unsupported files (must be quarantined, never copied raw)
    (inp / "misc" / "truncated.json").write_text('{"patient": "Rameshwar', encoding="utf-8")
    (inp / "misc" / "empty.csv").write_text("", encoding="utf-8")
    (inp / "misc" / "scanned.pdf").write_bytes(b"%PDF-1.4\n% Fake PDF with Rajesh Kumar Verma\n")

    truth = {
        "must_redact": [
            "Rajesh Kumar Verma",
            "Kavita Subramanian Iyer",
            "9811223344",
            "098223-34455",
            "4512 8899 3344",
            "91-1234-5678-9012",
            "ABCDE1234F",
            "PMJAY-UP-99887766",
            "KMC/26/991122",
            "KMC/26/991123",
            "सुनीता कुमारी",
            "रामपुर खुर्द",
            "Abdul Rahman",
            "अब्दुल रहमान",
            "Nasreen Begum",
            "Harish Chandra",
            "9876501234",
            "9876543210",
            "Maheshwar Verma",
            "9811223300",
        ],
        "must_redact_relatives": ["Ramesh"],  # S/o Ramesh
        "canaries": [
            "CANARY_ALPHA_9911",
            "CANARY_B64_7722",
            "CANARY_META_5544",
            "CANARY_FNAME_3311",
        ],
        "must_preserve": [
            "Dr. Ramesh",
            "Dr. Meera Nair",
            "C/O fever",
            "Dolo 650 BD x 5 days",
            "Ramipril 5 mg",
            "1-0-1",
            "Parkinson's disease",
            "BP 120/80",
            "245 mg/dL",
            "14.0 g/dL",
            "Acute bronchitis",
            "Azithromycin 500 mg OD x 3 days",
        ],
        "must_quarantine_count": 3,
    }
    (base_dir / "truth.json").write_text(json.dumps(truth, indent=2, ensure_ascii=False), encoding="utf-8")
    return truth


if __name__ == "__main__":
    build_adversarial_corpus(Path(__file__).resolve().parent)
    print("Generated adversarial corpus in tests/adversarial/input/")
