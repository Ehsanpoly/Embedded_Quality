@echo off
setlocal enabledelayedexpansion
cd /d "%~dp0"

if not exist .venv\Scripts\python.exe (
    echo Creating local virtual environment...
    py -3 -m venv .venv
    if errorlevel 1 exit /b 1
)

set PY=.venv\Scripts\python.exe
%PY% -m pip install --upgrade pip setuptools wheel
if errorlevel 1 exit /b 1
%PY% -m pip install -e ".[dev]"
if errorlevel 1 exit /b 1
%PY% main.py validate --with-pytest --clean
exit /b %ERRORLEVEL%
