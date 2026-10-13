from fastapi import APIRouter, Depends, Response
from sqlalchemy.orm import Session

from app.api.deps import CurrentUser
from app.core.database import get_db
from app.core.security import access_token_expires_in
from app.schemas.auth import (
    AccessTokenOut,
    AuthResponse,
    ChangePasswordIn,
    ClinicOut,
    LoginIn,
    MeResponse,
    RefreshIn,
    RegisterIn,
    UserOut,
)
from app.services import auth_service

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register", response_model=AuthResponse, status_code=201)
def register(payload: RegisterIn, db: Session = Depends(get_db)):
    """Create a new clinic and its first admin, and log them in."""
    return auth_service.build_auth_response(auth_service.register_clinic(db, payload))


@router.post("/login", response_model=AuthResponse)
def login(payload: LoginIn, db: Session = Depends(get_db)):
    return auth_service.build_auth_response(auth_service.authenticate(db, payload.email, payload.password))


@router.post("/refresh", response_model=AccessTokenOut)
def refresh(payload: RefreshIn, db: Session = Depends(get_db)):
    token = auth_service.refresh_access_token(db, payload.refresh_token)
    return AccessTokenOut(access_token=token, expires_in=access_token_expires_in())


@router.get("/me", response_model=MeResponse)
def me(user: CurrentUser):
    return MeResponse(user=UserOut.model_validate(user), clinic=ClinicOut.model_validate(user.clinic))


@router.post("/change-password", status_code=204)
def change_password(payload: ChangePasswordIn, user: CurrentUser, db: Session = Depends(get_db)):
    auth_service.change_password(db, user, payload)
    return Response(status_code=204)