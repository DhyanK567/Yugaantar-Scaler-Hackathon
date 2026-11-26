# MediLocker — Verification Guide

This guide documents how to reproduce all offline verification checks for **MediLocker / GuptKavach** (Track 3: Secret Wards).

## 1. One-Command Verification

### Windows (PowerShell)
```powershell
.\scripts\verify_submission.ps1
```

### Linux / macOS (Bash)
```bash
bash scripts/verify_submission.sh
```

Both scripts execute in sequence:
1. Python `>= 3.10` runtime check
2. Standalone engine execution: `python starter/main.py --input dev/input --output <temp_out>`
3. Official output contract check: `python validate_output.py --input dev/input --output <temp_out>`
4. Official submission readiness check: `python check_submission.py --repo starter --run`
5. Clinical Integrity suite (`tests/clinical_integrity/test_clinical_integrity.py`)
6. Clinical Drift suite (`tests/clinical_drift/test_clinical_drift.py`)
7. Privacy Attacks suite (`tests/privacy_attacks/test_privacy_attacks.py`)
8. Cryptography Security suite (`tests/cryptography/test_crypto_security.py`)
9. Multilingual PII suite (`tests/multilingual/test_multilingual_pii.py`)
10. Privacy Passport suite (`tests/privacy_passport/test_privacy_passport.py`)
11. Dynamic PDF Reporting suite (`tests/pdf_reporting/test_pdf_reporting.py`)
12. End-to-End Dataset Workflow suite (`tests/integration/test_dataset_workflow_e2e.py`)
13. Final Remediation Checks (`tests/integration/test_final_remediation.py`)

## 2. Manual Individual Commands

```powershell
# Validate output contract
python starter/main.py --input dev/input --output out_check
python validate_output.py --input dev/input --output out_check

# Run official submission checker
python check_submission.py --repo starter --run
```

## 3. Environment Notes
- All checks above run **100% offline** on CPU using Python standard library and local synthetic fixtures (`dev/input`).
- No LLM, hosted AI API, or internet connection is required.
