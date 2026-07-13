@echo off
setlocal
if not exist .venv (
  py -3 -m venv .venv
)
call .venv\Scripts\activate.bat
python -m pip install --upgrade pip setuptools wheel
python -m pip install -e ".[dev,package]"
python scripts\build_executable.py
if errorlevel 1 exit /b %errorlevel%
echo.
echo Executable created under dist\eqv-showcase.exe
