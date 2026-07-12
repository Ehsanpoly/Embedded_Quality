from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Any


@dataclass
class _Entry:
    value: Any
    expires_at: float | None = None

    def expired(self, now: float | None = None) -> bool:
        if self.expires_at is None:
            return False
        return (now if now is not None else time.monotonic()) >= self.expires_at


class FastStateStore:
    """Small Redis-inspired in-memory state store for host-side validation.

    The point is not to put Redis on the embedded target. The point is to keep a
    fast host-side state model: latest telemetry, memory CRC, firmware version,
    heartbeat TTL, dirty keys, and snapshots. That lets the framework skip slow
    hardware actions when state did not change and promote risky changes to
    deeper tests when they did change.
    """

    def __init__(self) -> None:
        self._kv: dict[str, _Entry] = {}
        self._streams: dict[str, list[dict[str, Any]]] = {}
        self._dirty: set[str] = set()

    def set(self, key: str, value: Any, *, ttl_s: float | None = None) -> None:
        expires_at = None if ttl_s is None else time.monotonic() + ttl_s
        old = self.get(key, default=None)
        self._kv[key] = _Entry(value=value, expires_at=expires_at)
        if old != value:
            self._dirty.add(key)

    def get(self, key: str, default: Any = None) -> Any:
        entry = self._kv.get(key)
        if entry is None:
            return default
        if entry.expired():
            self._kv.pop(key, None)
            self._dirty.add(key)
            return default
        return entry.value

    def append_stream(self, name: str, event: dict[str, Any]) -> None:
        self._streams.setdefault(name, []).append(dict(event))
        self._dirty.add(f"stream:{name}")

    def stream(self, name: str) -> list[dict[str, Any]]:
        return list(self._streams.get(name, []))

    def dirty_keys(self) -> list[str]:
        return sorted(self._dirty)

    def clear_dirty(self) -> None:
        self._dirty.clear()

    def snapshot(self) -> dict[str, Any]:
        # Force expiry cleanup while building a serializable view.
        keys = list(self._kv)
        return {key: self.get(key) for key in keys if key in self._kv}

    @staticmethod
    def diff(before: dict[str, Any], after: dict[str, Any]) -> dict[str, dict[str, Any]]:
        changes: dict[str, dict[str, Any]] = {}
        for key in sorted(set(before) | set(after)):
            if before.get(key) != after.get(key):
                changes[key] = {"before": before.get(key), "after": after.get(key)}
        return changes

    def has_changed(self, key: str, candidate_value: Any) -> bool:
        return self.get(key, default=object()) != candidate_value
