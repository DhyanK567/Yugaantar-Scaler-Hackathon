@echo off
setlocal
cd /d "%~dp0"

set "PY_EXE=%~dp0.venv\Scripts\python.exe"
if not exist "%PY_EXE%" (
    set "PY_EXE=python"
)

"%PY_EXE%" "%~dp0launcher\medilocker_launcher.py" %*
if errorlevel 1 (
    echo.
    echo MediLocker exited with an error.
    pause
)
endlocal
