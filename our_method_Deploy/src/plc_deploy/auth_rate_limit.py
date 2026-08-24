"""Cross-process login throttling for the single-tenant Web console."""

from __future__ import annotations

import fcntl
import hashlib
import json
import os
from pathlib import Path
from typing import Any


class LoginRateLimiter:
    """Persist failed-login windows behind a POSIX advisory lock.

    The production Web service runs more than one process, so an in-memory
    counter would let a client alternate between processes.  Only a hash of the
    client identity is persisted; passwords and usernames are never written.
    """

    def __init__(
        self,
        path: Path,
        *,
        max_failures: int = 5,
        window_seconds: int = 900,
        lockout_seconds: int = 900,
    ) -> None:
        if max_failures < 1 or window_seconds < 1 or lockout_seconds < 1:
            raise ValueError("login rate-limit values must be positive")
        self.path = path
        self.lock_path = path.with_suffix(path.suffix + ".lock")
        self.max_failures = max_failures
        self.window_seconds = window_seconds
        self.lockout_seconds = lockout_seconds

    @staticmethod
    def _key(identity: str) -> str:
        return hashlib.sha256(identity.encode("utf-8", errors="replace")).hexdigest()

    def _load(self) -> dict[str, dict[str, Any]]:
        try:
            value = json.loads(self.path.read_text(encoding="utf-8"))
        except (OSError, UnicodeError, json.JSONDecodeError):
            return {}
        return value if isinstance(value, dict) else {}

    def _save(self, state: dict[str, dict[str, Any]]) -> None:
        temporary = self.path.with_name(f".{self.path.name}.{os.getpid()}.tmp")
        temporary.write_text(
            json.dumps(state, separators=(",", ":")) + "\n", encoding="utf-8"
        )
        os.chmod(temporary, 0o600)
        temporary.replace(self.path)

    def _locked_state(self, operation):
        self.path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
        with self.lock_path.open("a+", encoding="utf-8") as lock:
            os.chmod(self.lock_path, 0o600)
            fcntl.flock(lock.fileno(), fcntl.LOCK_EX)
            state = self._load()
            result = operation(state)
            self._save(state)
            return result

    def retry_after(self, identity: str, *, now: float) -> int:
        key = self._key(identity)

        def inspect(state: dict[str, dict[str, Any]]) -> int:
            self._prune(state, now)
            entry = state.get(key, {})
            return max(0, int(float(entry.get("locked_until", 0)) - now + 0.999))

        return self._locked_state(inspect)

    def record_failure(self, identity: str, *, now: float) -> int:
        key = self._key(identity)

        def update(state: dict[str, dict[str, Any]]) -> int:
            self._prune(state, now)
            entry = state.setdefault(key, {"failures": [], "locked_until": 0})
            failures = [
                float(item) for item in entry.get("failures", [])
                if now - float(item) <= self.window_seconds
            ]
            failures.append(now)
            entry["failures"] = failures[-self.max_failures :]
            if len(failures) >= self.max_failures:
                entry["locked_until"] = now + self.lockout_seconds
            return max(0, int(float(entry.get("locked_until", 0)) - now + 0.999))

        return self._locked_state(update)

    def reset(self, identity: str, *, now: float) -> None:
        key = self._key(identity)

        def update(state: dict[str, dict[str, Any]]) -> None:
            self._prune(state, now)
            state.pop(key, None)

        self._locked_state(update)

    def _prune(self, state: dict[str, dict[str, Any]], now: float) -> None:
        horizon = now - max(self.window_seconds, self.lockout_seconds) * 2
        for key, entry in list(state.items()):
            failures = [float(item) for item in entry.get("failures", []) if float(item) >= horizon]
            locked_until = float(entry.get("locked_until", 0))
            if not failures and locked_until <= now:
                state.pop(key, None)
            else:
                entry["failures"] = failures
        if len(state) > 10_000:
            ordered = sorted(
                state,
                key=lambda item: max(
                    [float(value) for value in state[item].get("failures", [])] or [0]
                ),
            )
            for key in ordered[: len(state) - 10_000]:
                state.pop(key, None)
