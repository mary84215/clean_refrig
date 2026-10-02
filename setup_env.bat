@echo off
setlocal

rem ===== Settings =====
set "PYTHON_VERSION=3.14"
set "ENV_NAME=clean_frig"
set "REQ_FILE=%~dp0requirements.txt"
set "CONDA_ROOT=C:\ProgramData\miniconda3"
set "CHANNEL=conda-forge"
rem ====================

set "CONDA=%CONDA_ROOT%\condabin\conda.bat"
if not exist "%CONDA%" (
    echo [ERROR] conda not found at %CONDA_ROOT%
    exit /b 1
)
if not exist "%REQ_FILE%" (
    echo [ERROR] requirements file not found: %REQ_FILE%
    exit /b 1
)

call "%CONDA%" env list | findstr /b /c:"%ENV_NAME% " >nul
if errorlevel 1 (
    echo [INFO] Creating env "%ENV_NAME%" with Python %PYTHON_VERSION% ...
    call "%CONDA%" create -y -n %ENV_NAME% -c %CHANNEL% --override-channels python=%PYTHON_VERSION%
    if errorlevel 1 goto :fail
) else (
    echo [INFO] Env "%ENV_NAME%" already exists, skip creating.
)

echo [INFO] Installing packages from %REQ_FILE% ...
call "%CONDA%" run -n %ENV_NAME% python -m pip install -r "%REQ_FILE%"
if errorlevel 1 goto :fail

echo.
echo [DONE] Run "conda activate %ENV_NAME%" to use it.
exit /b 0

:fail
echo [ERROR] Setup failed.
exit /b 1
