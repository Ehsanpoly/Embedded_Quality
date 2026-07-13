#!/usr/bin/env python3
from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path


def main() -> int:
    if shutil.which("pyinstaller") is None:
        print("PyInstaller is not installed. Run: python -m pip install -e \".[package]\"")
        return 2
    cmd = [
        "pyinstaller",
        "--onefile",
        "--name",
        "eqv-showcase",
        "--clean",
        "--add-data",
        f"{Path('sample_data').as_posix()}{';' if sys.platform == 'win32' else ':'}sample_data",
        "main.py",
    ]
    print("$ " + " ".join(cmd))
    return subprocess.call(cmd)


if __name__ == "__main__":
    raise SystemExit(main())
