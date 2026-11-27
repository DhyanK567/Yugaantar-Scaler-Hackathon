#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO_ROOT"

FAILED=0
run_gate() {
  local name="$1"
  shift
  echo ""
  echo "=== GATE: $name ==="
  if "$@"; then
    echo "[PASS] $name"
  else
    echo "[FAIL] $name"
    FAILED=$((FAILED + 1))
  fi
}

run_gate "Frontend Lint & TypeCheck" bash -c "cd '$REPO_ROOT/frontend' && pnpm run lint && npx tsc --noEmit"
run_gate "Security Regression Gate" python3 scripts/security_regression_gate.py
run_gate "GuptKavach System & Auth Suite" python3 test_guptkavach_system.py
run_gate "Android Bridge Comprehensive Suite" pytest tests/android_bridge/test_android_bridge_comprehensive.py -v
run_gate "Milestone 17 & 18 Offline Verification" pytest tests/milestone_17/test_milestone_17.py tests/milestone_18/test_offline_verification.py -q
run_gate "Final Remediation Integration" python3 -m unittest tests/integration/test_final_remediation.py
run_gate "Independent Privacy & Clinical Eval" python3 tests/independent_eval/run_independent_eval.py
run_gate "Official Submission Check" python3 check_submission.py --repo starter --run

if [ "$FAILED" -gt 0 ]; then
  echo "VALIDATION FAILED ($FAILED mandatory gate(s) failed)"
  exit 1
fi
echo "ALL MANDATORY VALIDATION GATES PASSED"
