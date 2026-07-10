"""Password hashing + signed session tokens for the admin login (stdlib only).

No third-party crypto dependency and no secret in code:

* Passwords are hashed with **scrypt** (per-user random salt) and stored as a
  self-describing ``scrypt$n$r$p$salt_hex$hash_hex`` string. Verification is
  constant-time.
* Sessions are stateless **HMAC-SHA256 signed** bearer tokens carrying
  ``{"sub": username, "exp": epoch}``. The signing secret comes from
  ``NUDGEMATH_AUTH_SECRET``; if unset, a random per-process secret is generated,
  so existing tokens are invalidated on restart (documented behaviour).

The admin role is a superset of the anonymous student experience: a valid token
unlocks the answer-reveal and model-switch resolvers, nothing is taken away.
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import os
import secrets
import time

# scrypt cost parameters (RFC 7914). ``n`` must be a power of two. These give
# ~16 MB of work per hash — comfortably under the default OpenSSL maxmem.
_SCRYPT_N = 2**14
_SCRYPT_R = 8
_SCRYPT_P = 1
_SCRYPT_DKLEN = 32
_SALT_BYTES = 16

# Admin sessions last 12h; the client re-logs in after that.
SESSION_TTL_SECONDS = 12 * 3600

_PROCESS_SECRET: str | None = None


def hash_password(password: str) -> str:
    """Return a self-describing scrypt hash string for ``password``."""
    if not password:
        raise ValueError("password must not be empty")
    salt = secrets.token_bytes(_SALT_BYTES)
    derived = hashlib.scrypt(
        password.encode("utf-8"),
        salt=salt,
        n=_SCRYPT_N,
        r=_SCRYPT_R,
        p=_SCRYPT_P,
        dklen=_SCRYPT_DKLEN,
    )
    return f"scrypt${_SCRYPT_N}${_SCRYPT_R}${_SCRYPT_P}${salt.hex()}${derived.hex()}"


def verify_password(password: str, encoded: str) -> bool:
    """Constant-time check of ``password`` against a stored scrypt hash string."""
    try:
        scheme, n_s, r_s, p_s, salt_hex, hash_hex = encoded.split("$")
    except (ValueError, AttributeError):
        return False
    if scheme != "scrypt":
        return False
    try:
        n, r, p = int(n_s), int(r_s), int(p_s)
        salt = bytes.fromhex(salt_hex)
        expected = bytes.fromhex(hash_hex)
    except ValueError:
        return False
    derived = hashlib.scrypt(
        password.encode("utf-8"), salt=salt, n=n, r=r, p=p, dklen=len(expected)
    )
    return hmac.compare_digest(derived, expected)


def get_auth_secret() -> str:
    """Token-signing secret from ``NUDGEMATH_AUTH_SECRET``; a random per-process
    fallback otherwise (tokens then reset on restart). Never hardcoded."""
    env = os.environ.get("NUDGEMATH_AUTH_SECRET")
    if env and env.strip():
        return env.strip()
    global _PROCESS_SECRET
    if _PROCESS_SECRET is None:
        _PROCESS_SECRET = secrets.token_hex(32)
    return _PROCESS_SECRET


def _b64url_encode(raw: bytes) -> str:
    return base64.urlsafe_b64encode(raw).rstrip(b"=").decode("ascii")


def _b64url_decode(text: str) -> bytes:
    padding = "=" * (-len(text) % 4)
    return base64.urlsafe_b64decode(text + padding)


def create_token(
    username: str,
    *,
    ttl_seconds: int = SESSION_TTL_SECONDS,
    secret: str | None = None,
    now: float | None = None,
) -> str:
    """Issue a signed ``payload.signature`` bearer token for ``username``."""
    secret = secret or get_auth_secret()
    issued = int(now if now is not None else time.time())
    payload = {"sub": username, "exp": issued + ttl_seconds}
    payload_b64 = _b64url_encode(
        json.dumps(payload, separators=(",", ":")).encode("utf-8")
    )
    sig = hmac.new(
        secret.encode("utf-8"), payload_b64.encode("ascii"), hashlib.sha256
    ).digest()
    return f"{payload_b64}.{_b64url_encode(sig)}"


def verify_token(
    token: str, *, secret: str | None = None, now: float | None = None
) -> str | None:
    """Return the username for a valid, unexpired, correctly-signed token, else None."""
    secret = secret or get_auth_secret()
    try:
        payload_b64, sig_b64 = token.split(".")
    except (ValueError, AttributeError):
        return None
    expected_sig = hmac.new(
        secret.encode("utf-8"), payload_b64.encode("ascii"), hashlib.sha256
    ).digest()
    try:
        got_sig = _b64url_decode(sig_b64)
    except (ValueError, TypeError):
        return None
    if not hmac.compare_digest(expected_sig, got_sig):
        return None
    try:
        payload = json.loads(_b64url_decode(payload_b64))
    except (ValueError, TypeError):
        return None
    exp = payload.get("exp")
    sub = payload.get("sub")
    if not isinstance(exp, int) or not isinstance(sub, str):
        return None
    current = now if now is not None else time.time()
    if current >= exp:
        return None
    return sub
