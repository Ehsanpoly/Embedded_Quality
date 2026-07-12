@echo off
setlocal
python main.py smoke --output artifacts\smoke_report.json
python main.py memory-sanity --target sim
python main.py fast-gate
endlocal
