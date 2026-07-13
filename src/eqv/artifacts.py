from __future__ import annotations

import json
import platform
import sys
import tempfile
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .exceptions import ArtifactError, ErrorContext

DEFAULT_ARTIFACTS_DIR = Path("artifacts")


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def runtime_metadata() -> dict[str, Any]:
    """Small metadata block useful in CI and bench triage artifacts."""
    return {
        "generated_at_utc": utc_now_iso(),
        "python": sys.version.split()[0],
        "platform": platform.platform(),
        "machine": platform.machine(),
    }


def ensure_dir(path: str | Path) -> Path:
    directory = Path(path)
    directory.mkdir(parents=True, exist_ok=True)
    return directory


def _atomic_write_text(target: Path, text: str) -> None:
    target.parent.mkdir(parents=True, exist_ok=True)
    try:
        with tempfile.NamedTemporaryFile("w", encoding="utf-8", delete=False, dir=target.parent, suffix=".tmp") as tmp:
            tmp.write(text)
            temp_name = tmp.name
        Path(temp_name).replace(target)
    except OSError as exc:
        raise ArtifactError(
            f"failed to write artifact {target}",
            context=ErrorContext(operation="artifact_write", details={"path": str(target)}),
        ) from exc


def write_json(path: str | Path, payload: dict[str, Any] | list[Any]) -> Path:
    target = Path(path)
    _atomic_write_text(target, json.dumps(payload, indent=2, sort_keys=True))
    return target


def append_jsonl(path: str | Path, payload: dict[str, Any]) -> Path:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    try:
        with target.open("a", encoding="utf-8") as f:
            f.write(json.dumps(payload, sort_keys=True) + "\n")
    except OSError as exc:
        raise ArtifactError(
            f"failed to append artifact {target}",
            context=ErrorContext(operation="artifact_append", details={"path": str(target)}),
        ) from exc
    return target


@dataclass
class ArtifactManager:
    """Creates evidence files and a machine-readable manifest.

    Artifact creation is centralized so each validation command produces the
    same evidence shape: report files, log file, quality gate, and triage.
    """

    root: Path = DEFAULT_ARTIFACTS_DIR
    run_id: str | None = None
    manifest: list[dict[str, Any]] = field(default_factory=list)

    def __post_init__(self) -> None:
        self.root = ensure_dir(self.root)

    def path(self, name: str) -> Path:
        return self.root / name

    def write_json(self, name: str, payload: dict[str, Any] | list[Any], *, purpose: str) -> Path:
        path = write_json(self.path(name), payload)
        self.register(path, purpose=purpose)
        return path

    def register(self, path: str | Path, *, purpose: str) -> None:
        p = Path(path)
        self.manifest.append(
            {
                "path": str(p),
                "purpose": purpose,
                "exists": p.exists(),
                "size_bytes": p.stat().st_size if p.exists() else 0,
            }
        )

    def write_manifest(self, name: str = "artifact_manifest.json") -> Path:
        payload = {
            "run_id": self.run_id,
            "generated_at_utc": utc_now_iso(),
            "artifacts": self.manifest,
        }
        return write_json(self.path(name), payload)
