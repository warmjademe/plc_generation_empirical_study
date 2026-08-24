"""Subprocess helpers that do not leak verifier descendants on timeout."""

from __future__ import annotations

import os
import signal
import subprocess
import time
from pathlib import Path
from typing import Callable, Mapping, Sequence

from .cancellation import OperationCancelled


def _terminate_process_tree(process: subprocess.Popen[str], grace_seconds: float) -> None:
    """Terminate the POSIX process group created for ``process``.

    PLCverif launches a Java process which in turn launches nuXmv or CBMC.  The
    standard ``subprocess.run(..., timeout=...)`` only kills its direct child,
    allowing those descendants to keep consuming CPU.  Every command executed
    by :func:`run_captured` starts in a new session, so its process-group ID is
    the direct child's PID and can be terminated without touching another task.
    """

    if process.poll() is not None:
        return
    if os.name == "posix":
        try:
            os.killpg(process.pid, signal.SIGTERM)
        except ProcessLookupError:
            return
    else:  # pragma: no cover - the experiment executes on Linux
        process.terminate()

    def group_exists() -> bool:
        if os.name != "posix":
            return process.poll() is None
        try:
            os.killpg(process.pid, 0)
        except ProcessLookupError:
            return False
        return True

    deadline = time.monotonic() + grace_seconds
    while group_exists() and time.monotonic() < deadline:
        process.poll()
        time.sleep(0.05)
    if not group_exists():
        return
    if os.name == "posix":
        try:
            os.killpg(process.pid, signal.SIGKILL)
        except ProcessLookupError:
            return
    else:  # pragma: no cover - the experiment executes on Linux
        process.kill()


def run_captured(
    command: Sequence[str],
    *,
    cwd: str | Path | None = None,
    env: Mapping[str, str] | None = None,
    timeout: float | None = None,
    grace_seconds: float = 2.0,
    cancel_check: Callable[[], bool] | None = None,
    cancel_poll_seconds: float = 0.25,
) -> subprocess.CompletedProcess[str]:
    """Run a text command and kill its complete process group on timeout."""

    process = subprocess.Popen(
        tuple(command),
        cwd=cwd,
        env=env,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        start_new_session=os.name == "posix",
    )
    deadline = time.monotonic() + timeout if timeout is not None else None
    while True:
        if cancel_check is not None and cancel_check():
            _terminate_process_tree(process, grace_seconds)
            process.communicate()
            raise OperationCancelled("validator process cancelled by user")
        remaining = None if deadline is None else deadline - time.monotonic()
        if remaining is not None and remaining <= 0:
            _terminate_process_tree(process, grace_seconds)
            stdout, stderr = process.communicate()
            raise subprocess.TimeoutExpired(tuple(command), timeout, output=stdout, stderr=stderr)
        wait_for = remaining
        if cancel_check is not None:
            wait_for = min(cancel_poll_seconds, remaining) if remaining is not None else cancel_poll_seconds
        try:
            stdout, stderr = process.communicate(timeout=wait_for)
            break
        except subprocess.TimeoutExpired as exc:
            if deadline is not None and time.monotonic() >= deadline:
                _terminate_process_tree(process, grace_seconds)
                stdout, stderr = process.communicate()
                raise subprocess.TimeoutExpired(
                    tuple(command), timeout,
                    output=stdout if stdout is not None else exc.output,
                    stderr=stderr if stderr is not None else exc.stderr,
                ) from exc
            continue
    return subprocess.CompletedProcess(tuple(command), process.returncode, stdout, stderr)
