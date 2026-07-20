@echo off
:: run_checks.bat
:: Automatically generates config from providers.xlsx and runs model checks
::
:: Usage: run_checks.bat [output_dir] [env_file] [providers_file]

setlocal enabledelayedexpansion

:: Default values
set "OUTPUT_DIR=."
set "ENV_FILE=.env"
set "PROVIDERS_FILE=providers.json"
set "XLSX_FILE=providers.xlsx"

:: Parse arguments if provided
if not "%~1"=="" set "OUTPUT_DIR=%~1"
if not "%~2"=="" set "ENV_FILE=%~2"
if not "%~3"=="" set "PROVIDERS_FILE=%~3"

:: Check if Python is available
python --version >nul 2>&1
if errorlevel 1 (
    echo Error: Python is not installed or not in PATH
    pause
    exit /b 1
)

:: Check if providers.xlsx exists
if not exist "%XLSX_FILE%" (
    echo Error: %XLSX_FILE% not found
    pause
    exit /b 1
)

echo Generating config files from %XLSX_FILE%...
python check_models.py generate --xlsx "%XLSX_FILE%" --output-dir "%OUTPUT_DIR%" --env-file "%ENV_FILE%" --providers "%PROVIDERS_FILE%"

if errorlevel 1 (
    echo Error: Failed to generate config files
    pause
    exit /b 1
)

echo.
echo Running model checks with auto-update enabled...
python check_models.py check --auto-update --xlsx "%XLSX_FILE%" --config "%OUTPUT_DIR%\%PROVIDERS_FILE%" --env "%OUTPUT_DIR%\%ENV_FILE%" --merge-opencode

if errorlevel 1 (
    echo Error: Model checks failed
    pause
    exit /b 1
)

echo.
echo All done!
pause
