"""Auth domain: pure value types, password hashing, and JWT helpers.

All functions are stateless and carry no infrastructure dependencies.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

import bcrypt
import jwt


class AuthError(Exception):
    """Raised when credentials are invalid."""


class TokenError(Exception):
    """Raised when a JWT is missing, malformed, or expired."""


@dataclass(frozen=True)
class AuthUser:
    id: int
    email: str
    username: str
    password_hash: str
    created_at: datetime


# ---------------------------------------------------------------------------
# Password helpers
# ---------------------------------------------------------------------------


def hash_password(plain: str) -> str:
    """Return a bcrypt hash of *plain*."""
    return bcrypt.hashpw(plain.encode(), bcrypt.gensalt()).decode()


def verify_password(plain: str, hashed: str) -> bool:
    """Return ``True`` when *plain* matches *hashed*."""
    return bcrypt.checkpw(plain.encode(), hashed.encode())


# ---------------------------------------------------------------------------
# JWT helpers
# ---------------------------------------------------------------------------

_ALGORITHM = "HS256"
_SUBJECT_CLAIM = "sub"
_EXPIRY_CLAIM = "exp"


def issue_token(user_id: int, secret: str, expires_seconds: int) -> str:
    """Return a signed JWT encoding *user_id* as the subject."""
    payload = {
        _SUBJECT_CLAIM: str(user_id),
        _EXPIRY_CLAIM: datetime.now(UTC) + timedelta(seconds=expires_seconds),
    }
    return jwt.encode(payload, secret, algorithm=_ALGORITHM)


def verify_token(token: str, secret: str) -> int:
    """Decode *token* and return the user id.

    Raises :class:`TokenError` for any invalid or expired token.
    """
    try:
        payload = jwt.decode(token, secret, algorithms=[_ALGORITHM])
    except jwt.ExpiredSignatureError as exc:
        raise TokenError("Token has expired") from exc
    except jwt.InvalidTokenError as exc:
        raise TokenError("Invalid token") from exc

    subject = payload.get(_SUBJECT_CLAIM)
    if subject is None:
        raise TokenError("Token missing subject claim")

    try:
        return int(subject)
    except (ValueError, TypeError) as exc:
        raise TokenError("Token subject is not a valid user id") from exc
