PYTHON ?= python
VENV ?= .venv
ifeq ($(OS),Windows_NT)
  BIN := $(VENV)/Scripts
else
  BIN := $(VENV)/bin
endif
PY := $(BIN)/python
PIP := $(PY) -m pip

.PHONY: help venv install install-dev install-package smoke test fixture-demo validate gate triage coverage health clean ci demo exe

help:
	@echo "Embedded Quality Validation Showcase"
	@echo "  make install-dev  Create venv and install editable dev package"
	@echo "  make smoke        Run fast in-process validation workflow"
	@echo "  make test         Run pytest validation suite"
	@echo "  make fixture-demo Run advanced fixture pattern examples"
	@echo "  make validate     Run smoke + pytest + quality gate + triage"
	@echo "  make coverage     Run coverage report"
	@echo "  make clean        Remove generated artifacts and caches"
	@echo "  make exe          Build one-file CLI executable with PyInstaller"

venv:
	$(PYTHON) -m venv $(VENV)

install: venv
	$(PIP) install --upgrade pip setuptools wheel
	$(PIP) install -e .

install-dev: venv
	$(PIP) install --upgrade pip setuptools wheel
	$(PIP) install -e ".[dev]"

install-package: venv
	$(PIP) install --upgrade pip setuptools wheel
	$(PIP) install -e ".[dev,package]"

smoke:
	$(PY) main.py smoke --output artifacts/smoke_report.json

test:
	$(PY) -m pytest

fixture-demo:
	$(PY) -m pytest tests/test_advanced_fixtures.py -q

validate:
	$(PY) main.py validate --with-pytest --clean

gate:
	$(PY) scripts/run_quality_gate.py

triage:
	$(PY) scripts/triage_report.py

coverage:
	$(PY) -m pytest --cov=eqv --cov-report=term-missing

exe: install-package
	$(PY) scripts/build_executable.py

health:
	$(PY) scripts/check_repo_health.py

ci: health test gate triage

demo:
	$(PY) main.py smoke --output artifacts/demo_report.json
	$(PY) main.py bench-info --output artifacts/bench_info.json

clean:
	rm -rf .pytest_cache .ruff_cache .mypy_cache htmlcov dist build *.egg-info src/*.egg-info
	find . -type d -name __pycache__ -prune -exec rm -rf {} +
	rm -f artifacts/*.json artifacts/*.jsonl artifacts/*.xml artifacts/*.md .coverage

.PHONY: memory-sanity
memory-sanity:
	$(PY) main.py memory-sanity --target sim

.PHONY: nvm-check
nvm-check:
	$(PY) main.py nvm-check --target sim

.PHONY: fast-gate
fast-gate:
	$(PY) main.py fast-gate

.PHONY: endurance-plan
endurance-plan:
	$(PY) main.py endurance-plan
