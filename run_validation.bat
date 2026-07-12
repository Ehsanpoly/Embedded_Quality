@echo off
setlocal
python -m pip install --upgrade pip setuptools wheel
python -m pip install -e ".[dev]"
python main.py validate --with-pytest --clean
python main.py memory-sanity --target sim
python main.py nvm-check --target sim
python main.py fast-gate
python main.py endurance-plan
endlocal
