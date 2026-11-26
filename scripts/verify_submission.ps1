<#
.SYNOPSIS
    One-click offline verification script for MediLocker / GuptKavach (Track 3: Secret Wards).
.DESCRIPTION
    Verifies Python environment, executes the standalone privacy engine on dev/input,
    runs official evaluators (validate_output.py, check_submission.py), executes core
    regression/security/clinical/integration test suites, and prints a structured summary.
#>
$ErrorActionPreference = "Stop"

$RepoRoot = Split-Path -Parent $PSScriptRoot
Set-Location $RepoRoot

$TempOut = Join-Path $env:TEMP "medilocker_verify_out_$(Get-Date -Format 'yyyyMMdd_HHmmss')"
New-Item -ItemType Directory -Force -Path $TempOut | Out-Null

$Results = [ordered]@{}
$OverallExit = 0

function Run-Check {
    param(
        [string]$Name,
        [scriptblock]$Action
    )
    Write-Host "`n=== [$Name] ===" -ForegroundColor Cyan
    try {
        & $Action
        if ($LASTEXITCODE -ne 0) {
            $Results[$Name] = "FAIL (exit $LASTEXITCODE)"
            $script:OverallExit = 1
        } else {
            $Results[$Name] = "PASS"
        }
    } catch {
        Write-Host "ERROR: $_" -ForegroundColor Red
        $Results[$Name] = "FAIL"
        $script:OverallExit = 1
    }
}

# 1. Python environment check
Run-Check "Python Environment (>=3.10)" {
    python -c "import sys; assert sys.version_info >= (3, 10), sys.version; print('Python', sys.version.split()[0])"
}

# 2. Offline engine run on dev/input
Run-Check "Engine Run (starter/main.py)" {
    $env:RAKSHA_SECRET = "medilocker-verify-secret-2026"
    python starter/main.py --input dev/input --output $TempOut
}

# 3. Official output contract validation
Run-Check "Output Contract (validate_output.py)" {
    python validate_output.py --input dev/input --output $TempOut
}

# 4. Official submission checker
Run-Check "Submission Check (check_submission.py)" {
    python check_submission.py --repo starter --run
}

# 5. Core unit & adversarial test suites (stdlib-compatible)
$TestSuites = @(
    @{ Name = "Clinical Integrity"; Cmd = { python tests/clinical_integrity/test_clinical_integrity.py } },
    @{ Name = "Clinical Drift"; Cmd = { python tests/clinical_drift/test_clinical_drift.py } },
    @{ Name = "Privacy Attacks"; Cmd = { python tests/privacy_attacks/test_privacy_attacks.py } },
    @{ Name = "Cryptography Security"; Cmd = { python tests/cryptography/test_crypto_security.py } },
    @{ Name = "Filename Privacy (M16.1)"; Cmd = { python tests/cryptography/test_filename_privacy.py } },
    @{ Name = "Multilingual PII"; Cmd = { python tests/multilingual/test_multilingual_pii.py } },
    @{ Name = "Independent Benchmark"; Cmd = { python tests/independent_benchmark/test_independent_benchmark.py } },
    @{ Name = "Full Pipeline Integration"; Cmd = { python tests/integration/test_full_pipeline_integration.py } },
    @{ Name = "Dataset E2E Workflow"; Cmd = { python tests/integration/test_dataset_workflow_e2e.py } },
    @{ Name = "Final Remediation Checks"; Cmd = { python tests/integration/test_final_remediation.py } }
)

foreach ($Suite in $TestSuites) {
    Run-Check $Suite.Name $Suite.Cmd
}

# 6. Optional Ed25519 Privacy Passport suite (requires cryptography package)
Write-Host "`n=== [Privacy Passport (Ed25519)] ===" -ForegroundColor Cyan
python -c "import importlib.util, sys; sys.exit(0 if importlib.util.find_spec('cryptography') else 1)"
if ($LASTEXITCODE -eq 0) {
    Run-Check "Privacy Passport (Ed25519)" { python tests/privacy_passport/test_privacy_passport.py }
} else {
    Write-Host "SKIP: optional 'cryptography' package not installed in this Python runtime." -ForegroundColor Yellow
    $Results["Privacy Passport (Ed25519)"] = "SKIP (optional cryptography)"
}

# Cleanup temporary verification output
Remove-Item -Recurse -Force $TempOut -ErrorAction SilentlyContinue

Write-Host "`n============================================================" -ForegroundColor White
Write-Host "MEDILOCKER VERIFICATION SUMMARY" -ForegroundColor White
Write-Host "============================================================" -ForegroundColor White
foreach ($Key in $Results.Keys) {
    $Status = $Results[$Key]
    $Color = if ($Status -eq "PASS") { "Green" } else { "Red" }
    Write-Host ("{0,-40} : {1}" -f $Key, $Status) -ForegroundColor $Color
}
Write-Host "============================================================" -ForegroundColor White

if ($OverallExit -ne 0) {
    Write-Host "OVERALL RESULT: FAILED" -ForegroundColor Red
    exit 1
} else {
    Write-Host "OVERALL RESULT: PASS" -ForegroundColor Green
    exit 0
}
