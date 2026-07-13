#!/usr/bin/env python3
from __future__ import annotations

import importlib
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))


REQUIRED_PATHS = [
    Path("README.md"),
    Path("pyproject.toml"),
    Path("main.py"),
    Path("src/eqv/cli.py"),
    Path("src/eqv/validation_runner.py"),
    Path("src/eqv/pipeline.py"),
    Path("src/eqv/logging_config.py"),
    Path("src/eqv/exceptions.py"),
    Path("tests"),
    Path("docs/traceability_matrix.md"),
    Path(".github/workflows/ci.yml"),
]

REQUIRED_IMPORTS = ["eqv", "eqv.cli", "eqv.device", "eqv.transports", "eqv.validation_runner", "eqv.pipeline", "eqv.logging_config", "eqv.exceptions"]


def main() -> int:
    missing = [str(path) for path in REQUIRED_PATHS if not path.exists()]
    import_errors: list[str] = []
    for module in REQUIRED_IMPORTS:
        try:
            importlib.import_module(module)
        except Exception as exc:  # noqa: BLE001 - health check should report all import issues
            import_errors.append(f"{module}: {exc!r}")

    if missing or import_errors:
        print("Repository health check failed.")
        if missing:
            print("Missing paths:")
            for item in missing:
                print(f"  - {item}")
        if import_errors:
            print("Import errors:")
            for item in import_errors:
                print(f"  - {item}")
        return 2

    print("Repository health check passed: structure, imports, and showcase entry points are present.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
