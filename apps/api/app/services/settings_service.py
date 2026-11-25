"""Clinic profile (clinics table) and preferences (clinic_settings table)."""
import uuid

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models.core import ClinicSettings, User
from app.schemas.auth import ClinicOut
from app.schemas.settings import ClinicSettingsOut, ClinicSettingsPatch, PreferencesOut


def _get_or_create_preferences(db: Session, clinic_id: uuid.UUID) -> ClinicSettings:
    """Every clinic has exactly one preferences row, created with defaults on first use."""
    row = db.scalar(select(ClinicSettings).where(ClinicSettings.clinic_id == clinic_id))
    if row is None:
        db.add(ClinicSettings(clinic_id=clinic_id))
        try:
            db.commit()
        except IntegrityError:  # another request created it first
            db.rollback()
        row = db.scalar(select(ClinicSettings).where(ClinicSettings.clinic_id == clinic_id))
    return row


def _build(user: User, preferences: ClinicSettings) -> ClinicSettingsOut:
    return ClinicSettingsOut(
        clinic=ClinicOut.model_validate(user.clinic),
        preferences=PreferencesOut.model_validate(preferences),
    )


def get_clinic_settings(db: Session, user: User) -> ClinicSettingsOut:
    return _build(user, _get_or_create_preferences(db, user.clinic_id))


def update_clinic_settings(db: Session, user: User, patch: ClinicSettingsPatch) -> ClinicSettingsOut:
    preferences = _get_or_create_preferences(db, user.clinic_id)
    clinic = user.clinic
    if patch.clinic is not None:
        for field, value in patch.clinic.model_dump(exclude_unset=True).items():
            setattr(clinic, field, value)
    if patch.preferences is not None:
        for field, value in patch.preferences.model_dump(exclude_unset=True).items():
            setattr(preferences, field, value)
    db.commit()
    db.refresh(clinic)
    db.refresh(preferences)
    return _build(user, preferences)