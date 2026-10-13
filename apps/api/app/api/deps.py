"""API dependencies — implementation to be added."""
"""Shared request dependencies: who is logged in, and what they may do."""
import uuid
from typing import Annotated

from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.errors import ApiError
from app.core.security import decode_token
from app.models.core import User, UserRole

bearer_scheme = HTTPBearer(auto_error=False)


def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    db: Session = Depends(get_db),
) -> User:
    """The logged-in user, loaded fresh from the database on every request.

    Role changes and deactivation therefore take effect immediately, and the user's
    ``clinic_id`` comes from the database, never from the token or the request. Every
    clinic-owned query must filter by ``current_user.clinic_id``.
    """
    if credentials is None:
        raise ApiError(401, "NOT_AUTHENTICATED", "Login required")
    payload = decode_token(credentials.credentials, "access")
    try:
        user_id = uuid.UUID(payload["sub"])
    except (ValueError, TypeError):
        raise ApiError(401, "NOT_AUTHENTICATED", "Invalid token")
    user = db.get(User, user_id)
    if user is None or not user.is_active:
        raise ApiError(401, "NOT_AUTHENTICATED", "Invalid user")
    return user


CurrentUser = Annotated[User, Depends(get_current_user)]


def require_roles(*roles: UserRole):
    """Dependency factory: ``Depends(require_roles(UserRole.admin))``."""

    def checker(user: CurrentUser) -> User:
        if user.role not in roles:
            raise ApiError(403, "FORBIDDEN", "You do not have permission to do this")
        return user

    return checker


require_admin = require_roles(UserRole.admin)
