import pytest

from pnsi.auth.security import (
    csrf_valid,
    hash_password,
    hash_token,
    new_token,
    origin_allowed,
    tokens_match,
    verify_password,
)
from pnsi.auth.throttle import LoginThrottle

KEY = "test-secret-key"


def test_argon2_round_trip():
    h = hash_password("correct horse battery")
    assert h.startswith("$argon2id$")
    assert verify_password(h, "correct horse battery")
    assert not verify_password(h, "wrong password!!")


def test_missing_hash_never_verifies():
    assert not verify_password(None, "anything at all")


def test_short_password_rejected():
    with pytest.raises(ValueError):
        hash_password("short")


def test_tokens_are_random_and_only_hashes_compare():
    a, b = new_token(), new_token()
    assert a != b and len(a) >= 40
    h = hash_token(a, KEY)
    assert a not in h
    assert tokens_match(h, a, KEY)
    assert not tokens_match(h, b, KEY)
    assert not tokens_match(h, None, KEY)
    assert hash_token(a, "other-key") != h


def test_csrf_double_submit():
    csrf = new_token()
    stored = hash_token(csrf, KEY)
    assert csrf_valid("GET", None, None, stored, KEY)
    assert csrf_valid("POST", csrf, csrf, stored, KEY)
    assert not csrf_valid("POST", None, csrf, stored, KEY)
    assert not csrf_valid("PATCH", csrf, "different", stored, KEY)
    forged = new_token()
    assert not csrf_valid("DELETE", forged, forged, stored, KEY)


def test_origin_check():
    allowed = {"http://localhost:3000"}
    assert origin_allowed(None, allowed)
    assert origin_allowed("http://localhost:3000/", allowed)
    assert not origin_allowed("https://evil.example", allowed)


def test_throttle_blocks_then_expires():
    t = LoginThrottle(max_failures=3, window_seconds=60)
    for i in range(3):
        assert t.retry_after("k", now=i) is None
        t.record_failure("k", now=i)
    assert t.retry_after("k", now=3) is not None
    assert t.retry_after("k", now=100) is None
    t.record_failure("k", now=100)
    t.reset("k")
    assert t.retry_after("k", now=101) is None
