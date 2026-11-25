from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator

from app.models.core import UserRole


def _strip(value):
    return value.strip() if isinstance(value, str) else value


class RegisterIn(BaseModel):
    clinic_name: str = Field(min_length=2, max_length=150)
    first_name: str = Field(min_length=1, max_length=80)
    last_name: str = Field(min_length=1, max_length=80)
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)  # the cap stops oversized-input abuse of the hasher
    is_practitioner: bool = False

    _strip_text = field_validator("clinic_name", "first_name", "last_name", mode="before")(_strip)

    @field_validator("email")
    @classmethod
    def _lowercase_email(cls, value: str) -> str:
        return value.lower()


class LoginIn(BaseModel):
    # Deliberately a plain string: login must not reject an address a user already has.
    email: str = Field(min_length=1, max_length=255)
    password: str = Field(min_length=1, max_length=128)

    _strip_email = field_validator("email", mode="before")(_strip)


class RefreshIn(BaseModel):
    refresh_token: str = Field(min_length=1)


class ChangePasswordIn(BaseModel):
    current_password: str = Field(min_length=1, max_length=128)
    new_password: str = Field(min_length=8, max_length=128)


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    clinic_id: UUID
    first_name: str
    last_name: str
    email: str
    role: UserRole
    is_practitioner: bool
    is_active: bool


class ClinicOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    address: str | None = None
    phone: str | None = None


class AuthResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int
    user: UserOut
    clinic: ClinicOut


class AccessTokenOut(BaseModel):
    access_token: str
    expires_in: int


class MeResponse(BaseModel):
    user: UserOut
    clinic: ClinicOut