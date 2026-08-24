"""Cooperative cancellation shared by model orchestration and validators."""

from __future__ import annotations

from typing import Callable


class OperationCancelled(RuntimeError):
    """The user cancelled an active generation job."""


def raise_if_cancelled(cancel_check: Callable[[], bool] | None) -> None:
    if cancel_check is not None and cancel_check():
        raise OperationCancelled("job cancellation was requested")
