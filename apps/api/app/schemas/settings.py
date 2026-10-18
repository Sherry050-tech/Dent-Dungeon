import re
from zoneinfo import ZoneInfo

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.schemas.auth import ClinicOut

WEEKDAYS = ("mon", "tue", "wed", "thu", "fri", "sat", "sun")
_TIME_RE = re.compile(r"([01][0-9]|2[0-3]):[0-5][0-9]")
_CURRENCY_RE = re.compile(r"[A-Z]{3}")


def _not_null(value):
    if value is None:
        raise ValueError("This field cannot be empty")
    return value.strip() if isinstance(value, str) else value


class PreferencesOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    currency: str
    timezone: str
    working_hours: dict[str, list[str] | None]
    default_slot_min: int

    @field_validator("working_hours")
    @classmethod
    def _weekday_order(cls, value: dict) -> dict:
        # PostgreSQL JSONB does not keep key order, so always answer mon..sun (a closed day is null).
        return {day: value.get(day) for day in WEEKDAYS}


class ClinicSettingsOut(BaseModel):
    clinic: ClinicOut
    preferences: PreferencesOut


class ClinicProfilePatch(BaseModel):
    name: str | None = Field(default=None, min_length=2, max_length=150)
    address: str | None = Field(default=None, max_length=255)
    phone: str | None = Field(default=None, max_length=30)

    @field_validator("name", mode="before")
    @classmethod
    def _name_not_null(cls, value):
        return _not_null(value)

    @field_validator("address", "phone", mode="before")
    @classmethod
    def _blank_means_cleared(cls, value):
        # null or an empty string clears the field
        return (value.strip() or None) if isinstance(value, str) else value


class PreferencesPatch(BaseModel):
    currency: str | None = None
    timezone: str | None = None
    working_hours: dict[str, list[str] | None] | None = None
    default_slot_min: int | None = Field(default=None, ge=5, le=240)

    @field_validator("currency", "timezone", "working_hours", "default_slot_min", mode="before")
    @classmethod
    def _not_null_fields(cls, value):
        return _not_null(value)

    @field_validator("currency")
    @classmethod
    def _currency(cls, value: str) -> str:
        value = value.upper()
        if not _CURRENCY_RE.fullmatch(value):
            raise ValueError("Use a 3-letter currency code such as PKR")
        return value

    @field_validator("timezone")
    @classmethod
    def _timezone(cls, value: str) -> str:
        try:
            ZoneInfo(value)
        except Exception:
            raise ValueError("Unknown time zone. Use a name such as Asia/Karachi")
        return value

    @field_validator("working_hours")
    @classmethod
    def _working_hours(cls, value: dict) -> dict:
        """Replaces the whole schedule. Days that are left out are treated as closed."""
        unknown = set(value) - set(WEEKDAYS)
        if unknown:
            raise ValueError("Use the day names mon, tue, wed, thu, fri, sat, sun")
        result: dict[str, list[str] | None] = {}
        for day in WEEKDAYS:
            slot = value.get(day)
            if slot is None:
                result[day] = None
                continue
            if len(slot) != 2 or not all(_TIME_RE.fullmatch(t) for t in slot):
                raise ValueError(f'{day}: use ["09:00", "17:00"] (24-hour HH:MM)')
            if slot[0] >= slot[1]:
                raise ValueError(f"{day}: closing time must be after opening time")
            result[day] = [slot[0], slot[1]]
        return result


class ClinicSettingsPatch(BaseModel):
    clinic: ClinicProfilePatch | None = None
    preferences: PreferencesPatch | None = None