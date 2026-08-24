from __future__ import annotations

from pathlib import Path

from plc_deploy.auth_rate_limit import LoginRateLimiter


def test_login_failures_are_shared_and_lock_then_expire(tmp_path: Path) -> None:
    path = tmp_path / "auth.json"
    first = LoginRateLimiter(path, max_failures=3, window_seconds=60, lockout_seconds=120)
    second = LoginRateLimiter(path, max_failures=3, window_seconds=60, lockout_seconds=120)

    assert first.retry_after("client:user", now=1_000) == 0
    assert first.record_failure("client:user", now=1_000) == 0
    assert second.record_failure("client:user", now=1_010) == 0
    assert first.record_failure("client:user", now=1_020) == 120
    assert second.retry_after("client:user", now=1_030) == 110
    assert second.retry_after("another:user", now=1_030) == 0
    assert first.retry_after("client:user", now=1_141) == 0


def test_success_resets_login_failures_without_storing_identity(tmp_path: Path) -> None:
    path = tmp_path / "auth.json"
    limiter = LoginRateLimiter(path, max_failures=2, window_seconds=60, lockout_seconds=120)
    limiter.record_failure("203.0.113.8:operator", now=1_000)
    limiter.reset("203.0.113.8:operator", now=1_001)
    assert limiter.retry_after("203.0.113.8:operator", now=1_001) == 0
    assert "203.0.113.8" not in path.read_text(encoding="utf-8")
