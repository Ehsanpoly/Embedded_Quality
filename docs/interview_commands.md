# Interview Commands and Expected Outputs

## Fast 2-minute demo

```bash
python scripts/check_repo_health.py
python main.py smoke --output artifacts/local_validation_report.json
python main.py memory-sanity --target sim
python scripts/run_quality_gate.py
```

Expected evidence:

- `artifacts/local_validation_report.json`
- `artifacts/memory_sanity.json`
- `artifacts/quality_gate.json`
- `artifacts/validation.log`

## Full local validation

```bash
python main.py validate --with-pytest --clean
```

This runs smoke validation, pytest, quality gate, and triage report.

## Specific pytest selections

```bash
python -m pytest tests/test_protocol_frame.py -q
python -m pytest tests/test_device_workflows.py -q
python -m pytest tests/test_memory_diagnostics.py -q
python -m pytest tests/test_regression_field_log.py -q
python -m pytest tests/test_error_handling_logging.py -q
```

## Show a generated artifact

```bash
python -m json.tool artifacts/quality_gate.json
python -m json.tool artifacts/memory_sanity.json
```

## Real serial target placeholder

```bash
python -m pip install -e ".[dev,serial]"
python main.py memory-sanity --target serial --port COM4 --baudrate 115200
```

## Executable

```bash
python -m pip install -e ".[dev,package]"
python scripts/build_executable.py
./dist/eqv-showcase smoke
```
