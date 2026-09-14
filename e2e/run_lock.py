from __future__ import annotations

import json
import os
import socket
import time
from pathlib import Path


class RunAlreadyActive(RuntimeError):
    """Raised when another E2E process owns the run lock."""


class RunLock:
    """Cross-platform best-effort single-run lock using atomic file creation."""

    def __init__(self, path: Path, *, stale_after_seconds: float = 6 * 60 * 60) -> None:
        self.path = path
        self.stale_after_seconds = stale_after_seconds
        self._owned = False

    def acquire(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "pid": os.getpid(),
            "hostname": socket.gethostname(),
            "started_at": time.time(),
        }
        try:
            fd = os.open(self.path, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
        except FileExistsError as exc:
            if self._is_stale():
                try:
                    self.path.unlink()
                except FileNotFoundError:
                    pass
                else:
                    try:
                        fd = os.open(self.path, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
                    except FileExistsError as inner:
                        raise RunAlreadyActive(f"Another E2E run is active: {self.path}") from inner
            else:
                raise RunAlreadyActive(f"Another E2E run is active: {self.path}") from exc
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            json.dump(payload, handle)
        self._owned = True

    def _is_stale(self) -> bool:
        try:
            data = json.loads(self.path.read_text(encoding="utf-8"))
            started_at = float(data.get("started_at", 0))
        except (OSError, ValueError, TypeError, json.JSONDecodeError):
            started_at = 0
        return started_at <= 0 or (time.time() - started_at) > self.stale_after_seconds

    def release(self) -> None:
        if not self._owned:
            return
        try:
            self.path.unlink()
        except FileNotFoundError:
            pass
        finally:
            self._owned = False

    def __enter__(self) -> "RunLock":
        self.acquire()
        return self

    def __exit__(self, *_: object) -> None:
        self.release()
