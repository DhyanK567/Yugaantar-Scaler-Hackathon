# MediLocker Android — Reproducible Full Validation Script (Windows PowerShell)
$ErrorActionPreference = "Stop"
$RepoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
Set-Location $RepoRoot

$Failed = 0
function Run-Gate($Name, $ScriptBlock) {
    Write-Host "`n=== GATE: $Name ===" -ForegroundColor Cyan
    try {
        & $ScriptBlock
        if ($LASTEXITCODE -ne 0 -and $LASTEXITCODE -ne $null) {
            throw "Exit code $LASTEXITCODE"
        }
        Write-Host "[PASS] $Name" -ForegroundColor Green
    } catch {
        Write-Host "[FAIL] $Name : $_" -ForegroundColor Red
        $script:Failed++
    }
}

# 1. Frontend lint, typecheck & static export
Run-Gate "Frontend Lint & TypeCheck" {
    Push-Location "$RepoRoot\frontend"
    try {
        pnpm run lint
        if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
        npx tsc --noEmit
    } finally { Pop-Location }
}

# 2. Security regression gate
Run-Gate "Security Regression Gate" { python scripts\security_regression_gate.py }

# 3. System & Auth tests
Run-Gate "GuptKavach System & Auth Suite" { python test_guptkavach_system.py }

# 4. Android Bridge comprehensive suite (formats, Hindi filenames, security, CLI parity)
Run-Gate "Android Bridge Comprehensive Suite" { pytest tests\android_bridge\test_android_bridge_comprehensive.py -v }

# 5. Milestone 17 & 18 suites
Run-Gate "Milestone 17 & 18 Offline Verification" { pytest tests\milestone_17\test_milestone_17.py tests\milestone_18\test_offline_verification.py -q }

# 6. Integration remediation & Independent Eval
Run-Gate "Final Remediation Integration" { python -m unittest tests\integration\test_final_remediation.py }
Run-Gate "Independent Privacy & Clinical Eval" { python tests\independent_eval\run_independent_eval.py }

# 7. Official submission check
Run-Gate "Official Submission Check" { python check_submission.py --repo starter --run }

# 8. Android JVM Unit Tests
Run-Gate "Android JVM Unit Tests" {
    $env:JAVA_HOME = "$env:USERPROFILE\.jdks\jdk-17.0.21.1+2"
    $gradle = "C:\Users\Dell\.gradle\wrapper\dists\gradle-8.13-bin\5xuhj0ry160q40clulazy9h7d\gradle-8.13\bin\gradle.bat"
    Push-Location "$RepoRoot\android"
    try { & $gradle testReleaseUnitTest --no-daemon } finally { Pop-Location }
}

# 9. Emulator / Device Check
Write-Host "`n=== GATE: Android Emulator / Device Check ===" -ForegroundColor Cyan
$adb = "$env:LOCALAPPDATA\Android\Sdk\platform-tools\adb.exe"
if (Test-Path $adb) {
    $devs = (& $adb devices | Select-String "\tdevice$")
    if ($devs) {
        Write-Host "[PASS] Device attached: $devs" -ForegroundColor Green
    } else {
        Write-Host "[BLOCKED] No online Android device/emulator attached" -ForegroundColor Yellow
    }
} else {
    Write-Host "[BLOCKED] adb.exe not found" -ForegroundColor Yellow
}

if ($Failed -gt 0) {
    Write-Host "`nVALIDATION FAILED ($Failed mandatory gate(s) failed)" -ForegroundColor Red
    exit 1
}
Write-Host "`nALL MANDATORY VALIDATION GATES PASSED" -ForegroundColor Green
exit 0
