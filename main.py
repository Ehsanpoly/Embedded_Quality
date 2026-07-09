#!/usr/bin/env python3
"""Repository-level entry point for local demos.

Run without installing the package:

    python main.py
    python main.py smoke
    python main.py validate --with-pytest --clean

After `python -m pip install -e .`, the same commands are available as `eqv`.
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from eqv.cli import main  # noqa: E402


if __name__ == "__main__":
    raise SystemExit(main())
