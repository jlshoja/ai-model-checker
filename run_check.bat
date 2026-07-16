@echo off
setlocal enabledelayedexpansion

REM ============================================================
REM  ai-model-checker - Windows launcher
REM  Double-click this file, or run it from cmd/PowerShell.
REM  Any extra arguments you pass are forwarded to check_models.py
REM  Example:  run_check.bat --providers bluesminds
REM ============================================================

cd /d "%~dp0"

echo.
echo === ai-model-checker ===
echo Working directory: %cd%
echo.

REM --- Find Python -------------------------------------------------
where python >nul 2>nul
if %errorlevel% neq 0 (
    where py >nul 2>nul
    if %errorlevel% neq 0 (
        echo [ERROR] Python was not found in PATH.
        echo Install Python 3.9+ from https://www.python.org/downloads/
        echo and make sure "Add python.exe to PATH" is checked during install.
        pause
        exit /b 1
    ) else (
        set PYTHON=py
    )
) else (
    set PYTHON=python
)

echo Using Python: %PYTHON%
%PYTHON% --version

REM --- Create virtual environment if missing ------------------------
if not exist ".venv\Scripts\activate.bat" (
    echo.
    echo Creating virtual environment in .venv ...
    %PYTHON% -m venv .venv
    if %errorlevel% neq 0 (
        echo [ERROR] Failed to create virtual environment.
        pause
        exit /b 1
    )
)

call ".venv\Scripts\activate.bat"

REM --- Install/update dependencies ----------------------------------
echo.
echo Installing dependencies from requirements.txt ...
python -m pip install --quiet --upgrade pip
python -m pip install --quiet -r requirements.txt
if %errorlevel% neq 0 (
    echo [ERROR] Failed to install dependencies.
    pause
    exit /b 1
)

REM --- Make sure .env exists -----------------------------------------
if not exist ".env" (
    if exist ".env.example" (
        echo.
        echo No .env file found - creating one from .env.example
        copy ".env.example" ".env" >nul
        echo.
        echo [ACTION NEEDED] Open .env in a text editor and paste your real API keys,
        echo then run this script again.
        pause
        exit /b 0
    )
)

REM --- Make sure results folder exists --------------------------------
if not exist "results" mkdir "results"

REM --- Run the checker, forwarding any arguments ----------------------
echo.
echo Running check_models.py %*
echo.
python check_models.py %*

echo.
echo === Done. Report saved in the results folder. ===
pause
