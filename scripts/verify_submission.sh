#!/usr/bin/env bash
# One-click offline verification script for MediLocker / GuptKavach (Track 3: Secret Wards).
set -u

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO_ROOT"

TEMP_OUT="$(mktemp -d)"
cleanup() {
  rm -rf "$TEMP_OUT"
}
trap cleanup EXIT

OVERALL_EXIT=0
SUMMARY_LINES=()

run_check() {
  local name="$1"
  shift
  echo ""
  echo "=== [$name] ==="
  if "$@"; then
    SUMMARY_LINES+=("$(printf '%-40s : PASS' "$name")")
  else
    SUMMARY_LINES+=("$(printf '%-40s : FAIL' "$name")")
    OVERALL_EXIT=1
  fi
}

run_check "Python Environment (>=3.10)" python3 -c "import sys; assert sys.version_info >= (3, 10), sys.version; print('Python', sys.version.split()[0])"

export RAKSHA_SECRET="medilocker-verify-secret-2026"
run_check "Engine Run (starter/main.py)" python3 starter/main.py --input dev/input --output "$TEMP_OUT"
run_check "Output Contract (validate_output.py)" python3 validate_output.py --input dev/input --output "$TEMP_OUT"
run_check "Submission Check (check_submission.py)" python3 check_submission.py --repo starter --run

run_check "Clinical Integrity" python3 tests/clinical_integrity/test_clinical_integrity.py
run_check "Clinical Drift" python3 tests/clinical_drift/test_clinical_drift.py
run_check "Privacy Attacks" python3 tests/privacy_attacks/test_privacy_attacks.py
run_check "Cryptography Security" python3 tests/cryptography/test_crypto_security.py
run_check "Multilingual PII" python3 tests/multilingual/test_multilingual_pii.py
run_check "Independent Benchmark" python3 tests/independent_benchmark/test_independent_benchmark.py
run_check "Full Pipeline Integration" python3 tests/integration/test_full_pipeline_integration.py
run_check "Dataset E2E Workflow" python3 tests/integration/test_dataset_workflow_e2e.py
run_check "Final Remediation Checks" python3 tests/integration/test_final_remediation.py

echo ""
echo "=== [Privacy Passport (Ed25519)] ==="
if python3 -c "import cryptography" 2>/dev/null; then
  run_check "Privacy Passport (Ed25519)" python3 tests/privacy_passport/test_privacy_passport.py
else
  echo "SKIP: optional 'cryptography' package not installed in this Python runtime."
  SUMMARY_LINES+=("$(printf '%-40s : SKIP (optional cryptography)' 'Privacy Passport (Ed25519)')")
fi

echo ""
echo "============================================================"
echo "MEDILOCKER VERIFICATION SUMMARY"
echo "============================================================"
for line in "${SUMMARY_LINES[@]}"; do
  echo "$line"
done
echo "============================================================"

if [ "$OVERALL_EXIT" -ne 0 ]; then
  echo "OVERALL RESULT: FAILED"
  exit 1
fi
echo "OVERALL RESULT: PASS"
exit 0
