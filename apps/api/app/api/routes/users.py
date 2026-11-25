import uuid

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.api.deps import CurrentUser, require_admin
from app.core.database import get_db
from app.core.errors import ApiError
from app.models.core import User, UserRole
from app.schemas.auth import UserOut
from app.schemas.common import Paginated
from app.schemas.users import UserCreateIn, UserUpdateIn
from app.services import user_service

router = APIRouter(prefix="/users", tags=["users"])


@router.get("", response_model=Paginated[UserOut])
def list_users(
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
    role: UserRole | None = None,
    is_active: bool | None = None,
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
):
    items, total = user_service.list_users(db, admin.clinic_id, role=role, is_active=is_active, page=page, limit=limit)
    return Paginated[UserOut](items=[UserOut.model_validate(u) for u in items], total=total, page=page, limit=limit)


# IMPORTANT: this route must stay ABOVE /{user_id}, or "doctors" would be read as a user id.
@router.get("/doctors", response_model=Paginated[UserOut])
def list_doctors(user: CurrentUser, db: Session = Depends(get_db)):
    """Active users who can treat patients, for appointment dropdowns. Returns everyone (no paging)."""
    people = user_service.list_practitioners(db, user.clinic_id)
    return Paginated[UserOut](items=[UserOut.model_validate(u) for u in people],
                              total=len(people), page=1, limit=max(len(people), 1))


@router.post("", response_model=UserOut, status_code=201)
def create_user(payload: UserCreateIn, admin: User = Depends(require_admin), db: Session = Depends(get_db)):
    return user_service.create_user(db, admin.clinic_id, payload)


@router.get("/{user_id}", response_model=UserOut)
def get_user(user_id: uuid.UUID, current: CurrentUser, db: Session = Depends(get_db)):
    if current.role != UserRole.admin and current.id != user_id:
        raise ApiError(403, "FORBIDDEN", "You do not have permission to do this")
    return user_service.get_user_in_clinic(db, current.clinic_id, user_id)


@router.patch("/{user_id}", response_model=UserOut)
def update_user(user_id: uuid.UUID, payload: UserUpdateIn, admin: User = Depends(require_admin), db: Session = Depends(get_db)):
    return user_service.update_user(db, admin.clinic_id, user_id, payload)