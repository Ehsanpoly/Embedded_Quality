@echo off
setlocal
cd /d "%~dp0"
set PY=python
if exist .venv\Scripts\python.exe set PY=.venv\Scripts\python.exe
%PY% main.py smoke --output artifacts\demo_report.json
%PY% main.py bench-info --output artifacts\bench_info.json
endlocal
