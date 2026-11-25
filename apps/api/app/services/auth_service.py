"""Business rules for registration, login, token refresh and password change."""
import uuid
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.errors import ApiError
from app.core.security import (
    access_token_expires_in,
    create_access_token,
    create_refresh_token,
    decode_token,
    hash_password,
    verify_dummy_password,
    verify_password,
)
from app.models.core import Clinic, User, UserRole
from app.schemas.auth import AuthResponse, ChangePasswordIn, ClinicOut, RegisterIn, UserOut


def normalize_email(email: str) -> str:
    return email.strip().lower()


def build_auth_response(user: User) -> AuthResponse:
    return AuthResponse(
        access_token=create_access_token(user.id),
        refresh_token=create_refresh_token(user.id),
        expires_in=access_token_expires_in(),
        user=UserOut.model_validate(user),
        clinic=ClinicOut.model_validate(user.clinic),
    )


def register_clinic(db: Session, data: RegisterIn) -> User:
    """Create a NEW clinic and its first admin in one transaction. Never joins an existing clinic."""
    email = normalize_email(data.email)
    if db.scalar(select(User.id).where(User.email == email)) is not None:
        raise ApiError(409, "EMAIL_TAKEN", "This email is already registered", {"email": "This email is already registered"})

    clinic = Clinic(name=data.clinic_name)
    user = User(
        clinic=clinic,
        email=email,
        hashed_password=hash_password(data.password),
        first_name=data.first_name,
        last_name=data.last_name,
        role=UserRole.admin,
        is_practitioner=data.is_practitioner,
        is_active=True,
        last_login_at=datetime.now(timezone.utc),
    )
    db.add(user)
    try:
        db.commit()
    except IntegrityError:  # two sign-ups with the same email at the same moment
        db.rollback()
        raise ApiError(409, "EMAIL_TAKEN", "This email is already registered", {"email": "This email is already registered"})
    db.refresh(user)
    return user


def authenticate(db: Session, email: str, password: str) -> User:
    user = db.scalar(select(User).where(User.email == normalize_email(email)))
    if user is None:
        verify_dummy_password(password)
        raise ApiError(401, "INVALID_CREDENTIALS", "Email or password is incorrect")
    if not verify_password(password, user.hashed_password):
        raise ApiError(401, "INVALID_CREDENTIALS", "Email or password is incorrect")
    # Only after the password is right, so this message cannot be used to discover accounts.
    if not user.is_active:
        raise ApiError(403, "ACCOUNT_INACTIVE", "This account has been deactivated. Contact your clinic administrator.")
    user.last_login_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(user)
    return user


def refresh_access_token(db: Session, refresh_token: str) -> str:
    payload = decode_token(refresh_token, "refresh")
    try:
        user = db.get(User, uuid.UUID(payload["sub"]))
    except (ValueError, TypeError):
        raise ApiError(401, "NOT_AUTHENTICATED", "Invalid token")
    if user is None or not user.is_active:
        raise ApiError(401, "NOT_AUTHENTICATED", "Invalid user")
    return create_access_token(user.id)


def change_password(db: Session, user: User, data: ChangePasswordIn) -> None:
    if not verify_password(data.current_password, user.hashed_password):
        raise ApiError(400, "WRONG_PASSWORD", "Current password is incorrect", {"current_password": "Current password is incorrect"})
    if data.new_password == data.current_password:
        raise ApiError(422, "VALIDATION_ERROR", "Validation error", {"new_password": "Choose a password different from the current one"})
    user.hashed_password = hash_password(data.new_password)
    db.commit()