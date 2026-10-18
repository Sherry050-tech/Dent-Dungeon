"""Staff management. Every query is scoped to the caller's clinic."""
import uuid

from sqlalchemy import func, or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.errors import ApiError
from app.core.security import hash_password
from app.models.core import User, UserRole
from app.schemas.users import UserCreateIn, UserUpdateIn

_EMAIL_TAKEN = ApiError(409, "EMAIL_TAKEN", "This email is already registered", {"email": "This email is already registered"})


def get_user_in_clinic(db: Session, clinic_id: uuid.UUID, user_id: uuid.UUID) -> User:
    """A user of ANOTHER clinic is reported as 404, exactly like one that does not exist."""
    user = db.scalar(select(User).where(User.id == user_id, User.clinic_id == clinic_id))
    if user is None:
        raise ApiError(404, "NOT_FOUND", "User not found")
    return user


def list_users(db: Session, clinic_id: uuid.UUID, *, role: UserRole | None, is_active: bool | None,
               page: int, limit: int) -> tuple[list[User], int]:
    conditions = [User.clinic_id == clinic_id]
    if role is not None:
        conditions.append(User.role == role)
    if is_active is not None:
        conditions.append(User.is_active == is_active)
    total = db.scalar(select(func.count()).select_from(User).where(*conditions)) or 0
    items = db.scalars(
        select(User).where(*conditions)
        .order_by(User.first_name, User.last_name, User.id)
        .offset((page - 1) * limit).limit(limit)
    ).all()
    return list(items), total


def list_practitioners(db: Session, clinic_id: uuid.UUID) -> list[User]:
    """Active users who can treat patients: role doctor, or any role with is_practitioner."""
    return list(db.scalars(
        select(User)
        .where(User.clinic_id == clinic_id, User.is_active.is_(True),
               or_(User.role == UserRole.doctor, User.is_practitioner.is_(True)))
        .order_by(User.first_name, User.last_name, User.id)
    ).all())


def create_user(db: Session, clinic_id: uuid.UUID, data: UserCreateIn) -> User:
    if db.scalar(select(User.id).where(User.email == data.email.lower())) is not None:
        raise _EMAIL_TAKEN
    user = User(
        clinic_id=clinic_id,  # always the admin's own clinic, never taken from the request
        email=data.email.lower(),
        hashed_password=hash_password(data.temporary_password),
        first_name=data.first_name,
        last_name=data.last_name,
        role=data.role,
        is_practitioner=data.is_practitioner,
        is_active=True,
    )
    db.add(user)
    try:
        db.commit()
    except IntegrityError:  # same email created twice at the same moment
        db.rollback()
        raise _EMAIL_TAKEN
    db.refresh(user)
    return user


def update_user(db: Session, clinic_id: uuid.UUID, user_id: uuid.UUID, data: UserUpdateIn) -> User:
    changes = data.model_dump(exclude_unset=True)

    # Lock this clinic's active admins first, so two admins demoting each other at the
    # same moment cannot leave the clinic with nobody in charge.
    admins = db.scalars(
        select(User).where(User.clinic_id == clinic_id, User.role == UserRole.admin, User.is_active.is_(True))
        .with_for_update()
    ).all()
    user = get_user_in_clinic(db, clinic_id, user_id)

    was_active_admin = user.role == UserRole.admin and user.is_active
    stays_active_admin = changes.get("role", user.role) == UserRole.admin and changes.get("is_active", user.is_active)
    if was_active_admin and not stays_active_admin and not any(a.id != user.id for a in admins):
        raise ApiError(400, "LAST_ADMIN", "A clinic must keep at least one active administrator")

    for field, value in changes.items():
        setattr(user, field, value)
    db.commit()
    db.refresh(user)
    return user