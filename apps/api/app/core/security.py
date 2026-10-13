"""Security and authentication — implementation to be added."""
"""Password hashing (Argon2) and JWT access/refresh tokens."""
from datetime import datetime, timedelta, timezone
from uuid import UUID

import jwt
from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerificationError

from app.core.config import settings
from app.core.errors import ApiError

_ALGORITHM = "HS256"
_hasher = PasswordHasher()
# Checked when a login email does not exist, so "unknown email" and "wrong password"
# take the same time and cannot be told apart by timing.
_DUMMY_HASH = _hasher.hash("dent-dungeon-timing-equalizer")


def hash_password(password: str) -> str:
    return _hasher.hash(password)


def verify_password(password: str, hashed: str) -> bool:
    try:
        return _hasher.verify(hashed, password)
    except (VerificationError, InvalidHashError):
        return False


def verify_dummy_password(password: str) -> None:
    verify_password(password, _DUMMY_HASH)


def _create_token(user_id: UUID | str, kind: str, lifetime: timedelta) -> str:
    now = datetime.now(timezone.utc)
    payload = {"sub": str(user_id), "type": kind, "iat": now, "exp": now + lifetime}
    return jwt.encode(payload, settings.secret_key, algorithm=_ALGORITHM)


def create_access_token(user_id: UUID | str, lifetime: timedelta | None = None) -> str:
    return _create_token(user_id, "access", lifetime or timedelta(minutes=settings.access_token_expire_minutes))


def create_refresh_token(user_id: UUID | str, lifetime: timedelta | None = None) -> str:
    return _create_token(user_id, "refresh", lifetime or timedelta(days=settings.refresh_token_expire_days))


def access_token_expires_in() -> int:
    return settings.access_token_expire_minutes * 60


def decode_token(token: str, expected_type: str) -> dict:
    """Return the token payload, or raise a 401 ApiError. An access token is never accepted as a refresh token."""
    try:
        payload = jwt.decode(token, settings.secret_key, algorithms=[_ALGORITHM],
                             options={"require": ["exp", "sub", "type"]}, leeway=5)
    except jwt.ExpiredSignatureError:
        raise ApiError(401, "TOKEN_EXPIRED", "Token has expired")
    except jwt.InvalidTokenError:
        raise ApiError(401, "NOT_AUTHENTICATED", "Invalid token")
    if payload.get("type") != expected_type:
        raise ApiError(401, "NOT_AUTHENTICATED", "Invalid token")
    return payload
