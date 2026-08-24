from plc_deploy.main import _make_session, _valid_session, settings


def test_signed_session_accepts_valid_user_and_rejects_tampering() -> None:
    token = _make_session(settings.login_username, now=1_000)
    assert _valid_session(token, now=1_001)
    assert not _valid_session(token + "x", now=1_001)


def test_signed_session_expires() -> None:
    token = _make_session(settings.login_username, now=1_000)
    assert not _valid_session(token, now=1_001 + settings.session_ttl_seconds)
