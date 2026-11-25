from pydantic import BaseModel, EmailStr, Field, field_validator

from app.models.core import UserRole


def _strip(value):
    return value.strip() if isinstance(value, str) else value


class UserCreateIn(BaseModel):
    first_name: str = Field(min_length=1, max_length=80)
    last_name: str = Field(min_length=1, max_length=80)
    email: EmailStr
    temporary_password: str = Field(min_length=8, max_length=128)
    role: UserRole
    is_practitioner: bool = False

    _strip_names = field_validator("first_name", "last_name", mode="before")(_strip)

    @field_validator("email")
    @classmethod
    def _lowercase_email(cls, value: str) -> str:
        return value.lower()


class UserUpdateIn(BaseModel):
    """Partial update: send only the fields that change. Email and password are not editable here."""

    first_name: str | None = Field(default=None, min_length=1, max_length=80)
    last_name: str | None = Field(default=None, min_length=1, max_length=80)
    role: UserRole | None = None
    is_practitioner: bool | None = None
    is_active: bool | None = None

    @field_validator("first_name", "last_name", "role", "is_practitioner", "is_active", mode="before")
    @classmethod
    def _not_null(cls, value):
        # Omit a field to leave it alone. Sending null for it is a mistake, not "no change".
        if value is None:
            raise ValueError("This field cannot be empty")
        return _strip(value)