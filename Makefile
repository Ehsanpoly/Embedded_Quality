PYTHON ?= python
VENV ?= .venv
ifeq ($(OS),Windows_NT)
  BIN := $(VENV)/Scripts
else
  BIN := $(VENV)/bin
endif
PY := $(BIN)/python
PIP := $(PY) -m pip

.PHONY: help venv install install-dev smoke test validate gate triage coverage health clean ci demo

help:
	@echo "Embedded Quality Validation Showcase"
	@echo "  make install-dev  Create venv and install editable dev package"
	@echo "  make smoke        Run fast in-process validation workflow"
	@echo "  make test         Run pytest validation suite"
	@echo "  make validate     Run smoke + pytest + quality gate + triage"
	@echo "  make coverage     Run coverage report"
	@echo "  make clean        Remove generated artifacts and caches"

venv:
	$(PYTHON) -m venv $(VENV)

install: venv
	$(PIP) install --upgrade pip setuptools wheel
	$(PIP) install -e .

install-dev: venv
	$(PIP) install --upgrade pip setuptools wheel
	$(PIP) install -e ".[dev]"

smoke:
	$(PYTHON) main.py smoke --output artifacts/smoke_report.json

test:
	$(PYTHON) -m pytest

validate:
	$(PYTHON) main.py validate --with-pytest --clean

gate:
	$(PYTHON) scripts/run_quality_gate.py

triage:
	$(PYTHON) scripts/triage_report.py

coverage:
	$(PYTHON) -m pytest --cov=eqv --cov-report=term-missing

health:
	$(PYTHON) scripts/check_repo_health.py

ci: health test gate triage

demo:
	$(PYTHON) main.py smoke --output artifacts/demo_report.json
	$(PYTHON) main.py bench-info --output artifacts/bench_info.json

clean:
	rm -rf .pytest_cache .ruff_cache .mypy_cache htmlcov dist build *.egg-info src/*.egg-info
	find . -type d -name __pycache__ -prune -exec rm -rf {} +
	rm -f artifacts/*.json artifacts/*.jsonl artifacts/*.xml artifacts/*.md .coverage

.PHONY: memory-sanity
memory-sanity:
	$(PYTHON) main.py memory-sanity --target sim

.PHONY: nvm-check
nvm-check:
	$(PYTHON) main.py nvm-check --target sim

.PHONY: fast-gate
fast-gate:
	$(PYTHON) main.py fast-gate

.PHONY: endurance-plan
endurance-plan:
	$(PYTHON) main.py endurance-plan
