"""Local authentication primitives for the CommandIA demo API.

Passwords are hashed with PBKDF2-SHA256. Sessions are stateless, signed
tokens stored in an HttpOnly cookie so they survive a backend restart.
"""
import base64
import hashlib
import hmac
import os
import time
from typing import Optional

COOKIE_NAME = "commandia_session"
SESSION_TTL_SECONDS = 7 * 24 * 60 * 60
PBKDF2_ITERATIONS = 260_000

# A stable local default keeps demo sessions valid across restarts. Production
# deployments must set COMMANDIA_SESSION_SECRET to a private random value.
SESSION_SECRET = os.getenv("COMMANDIA_SESSION_SECRET", "commandia-local-development-secret")


def _b64encode(value: bytes) -> str:
    return base64.urlsafe_b64encode(value).decode("ascii").rstrip("=")


def _b64decode(value: str) -> bytes:
    padding = "=" * (-len(value) % 4)
    return base64.urlsafe_b64decode(value + padding)


def hash_password(password: str) -> str:
    salt = os.urandom(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, PBKDF2_ITERATIONS)
    return f"pbkdf2_sha256${PBKDF2_ITERATIONS}${_b64encode(salt)}${_b64encode(digest)}"


def verify_password(password: str, encoded: str) -> bool:
    try:
        algorithm, iterations, salt, expected = encoded.split("$", 3)
        if algorithm != "pbkdf2_sha256":
            return False
        digest = hashlib.pbkdf2_hmac(
            "sha256",
            password.encode("utf-8"),
            _b64decode(salt),
            int(iterations),
        )
    except (ValueError, TypeError):
        return False
    return hmac.compare_digest(_b64encode(digest), expected)


def _signature(payload: str) -> str:
    return hmac.new(
        SESSION_SECRET.encode("utf-8"),
        payload.encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()


def create_session_token(email: str) -> str:
    expires = int(time.time()) + SESSION_TTL_SECONDS
    payload = _b64encode(f"{email}|{expires}".encode("utf-8"))
    return f"{payload}.{_signature(payload)}"


def verify_session_token(token: Optional[str]) -> Optional[str]:
    if not token or "." not in token:
        return None
    payload, signature = token.rsplit(".", 1)
    if not hmac.compare_digest(signature, _signature(payload)):
        return None
    try:
        email, expires = _b64decode(payload).decode("utf-8").rsplit("|", 1)
        if time.time() > int(expires):
            return None
    except (ValueError, UnicodeDecodeError):
        return None
    return email
