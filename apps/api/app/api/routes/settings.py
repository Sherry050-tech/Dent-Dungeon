from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import CurrentUser, require_admin
from app.core.database import get_db
from app.models.core import User
from app.schemas.settings import ClinicSettingsOut, ClinicSettingsPatch
from app.services import settings_service

router = APIRouter(prefix="/settings", tags=["settings"])


@router.get("/clinic", response_model=ClinicSettingsOut)
def get_clinic_settings(user: CurrentUser, db: Session = Depends(get_db)):
    return settings_service.get_clinic_settings(db, user)


@router.patch("/clinic", response_model=ClinicSettingsOut)
def update_clinic_settings(payload: ClinicSettingsPatch, admin: User = Depends(require_admin), db: Session = Depends(get_db)):
    return settings_service.update_clinic_settings(db, admin, payload)