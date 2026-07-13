from __future__ import annotations

import logging
import sys
import time
from pathlib import Path


def configure_logging(
    *,
    level: str = "INFO",
    log_file: str | Path = "artifacts/validation.log",
    force: bool = False,
) -> Path:
    """Configure console + file logging for local and CI validation runs.

    The log file is intentionally treated as a validation artifact. In real HIL
    benches, this file would be uploaded together with JUnit, TX/RX traces,
    firmware version, and cloud correlation IDs.
    """

    target = Path(log_file)
    target.parent.mkdir(parents=True, exist_ok=True)
    numeric_level = getattr(logging, level.upper(), logging.INFO)

    logging.Formatter.converter = staticmethod(time.gmtime)  # UTC timestamps for CI/bench correlation
    logging.basicConfig(
        level=numeric_level,
        format="%(asctime)sZ %(levelname)-8s %(name)s :: %(message)s",
        datefmt="%Y-%m-%dT%H:%M:%S",
        handlers=[
            logging.StreamHandler(sys.stdout),
            logging.FileHandler(target, encoding="utf-8"),
        ],
        force=force,
    )
    logging.getLogger("eqv").debug("logging configured level=%s file=%s", level, target)
    return target
