"""Password hashing, opaque tokens and CSRF checks (decision D13)."""

from __future__ import annotations

import contextlib
import hashlib
import hmac
import secrets

from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerificationError, VerifyMismatchError

_hasher = PasswordHasher()  # argon2id with the library's current recommended parameters

# Verified against when the account does not exist, so timing does not reveal it.
_DUMMY_HASH = _hasher.hash(secrets.token_urlsafe(16))

MIN_PASSWORD_LENGTH = 12
UNSAFE_METHODS = frozenset({"POST", "PUT", "PATCH", "DELETE"})


def hash_password(password: str) -> str:
    if len(password) < MIN_PASSWORD_LENGTH:
        raise ValueError(f"password must have at least {MIN_PASSWORD_LENGTH} characters")
    return _hasher.hash(password)


def verify_password(password_hash: str | None, password: str) -> bool:
    if password_hash is None:
        # Same work as a real check, then refuse.
        with contextlib.suppress(VerificationError):
            _hasher.verify(_DUMMY_HASH, password)
        return False
    try:
        return _hasher.verify(password_hash, password)
    except (VerifyMismatchError, VerificationError, InvalidHashError):
        return False


def needs_rehash(password_hash: str) -> bool:
    return _hasher.check_needs_rehash(password_hash)


def new_token() -> str:
    return secrets.token_urlsafe(32)


def hash_token(token: str, secret_key: str) -> str:
    """Keyed hash of a session or CSRF token. Only this value is stored."""
    return hmac.new(secret_key.encode(), token.encode(), hashlib.sha256).hexdigest()


def tokens_match(token_hash: str, token: str | None, secret_key: str) -> bool:
    if not token:
        return False
    return hmac.compare_digest(token_hash, hash_token(token, secret_key))


def origin_allowed(origin: str | None, allowed: set[str]) -> bool:
    """Browsers send Origin on unsafe requests. Absent means a non-browser client."""
    if origin is None:
        return True
    return origin.rstrip("/") in {a.rstrip("/") for a in allowed}


def csrf_valid(
    method: str,
    header_token: str | None,
    cookie_token: str | None,
    session_csrf_hash: str,
    secret_key: str,
) -> bool:
    """Double submit: header equals cookie, and both match the session's CSRF token."""
    if method.upper() not in UNSAFE_METHODS:
        return True
    if not header_token or not cookie_token:
        return False
    if not hmac.compare_digest(header_token, cookie_token):
        return False
    return tokens_match(session_csrf_hash, header_token, secret_key)
