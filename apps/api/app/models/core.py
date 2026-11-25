import copy
import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, String, Boolean, DateTime, ForeignKey, Enum, Integer, JSON, true
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import relationship
import enum

from app.core.database import Base

class UserRole(str, enum.Enum):
    admin = "admin"
    doctor = "doctor"
    receptionist = "receptionist"

class Clinic(Base):
    __tablename__ = "clinics"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String, nullable=False)
    address = Column(String, nullable=True)
    phone = Column(String, nullable=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    users = relationship("User", back_populates="clinic")


class User(Base):
    __tablename__ = "users"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    clinic_id = Column(UUID(as_uuid=True), ForeignKey("clinics.id", ondelete="CASCADE"), nullable=False)
    
    email = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    first_name = Column(String, nullable=False)
    last_name = Column(String, nullable=False)
    
    role = Column(Enum(UserRole), nullable=False)
    is_practitioner = Column(Boolean, nullable=False, default=False)
    is_active = Column(Boolean, nullable=False, default=True, server_default=true())
    last_login_at = Column(DateTime(timezone=True), nullable=True)
    
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    clinic = relationship("Clinic", back_populates="users")

    

DEFAULT_WORKING_HOURS = {
    "mon": ["09:00", "17:00"],
    "tue": ["09:00", "17:00"],
    "wed": ["09:00", "17:00"],
    "thu": ["09:00", "17:00"],
    "fri": ["09:00", "17:00"],
    "sat": ["09:00", "17:00"],
    "sun": None,
}


def default_working_hours() -> dict:
    return copy.deepcopy(DEFAULT_WORKING_HOURS)


class ClinicSettings(Base):
    """Preferences for one clinic. Clinic identity (name, address, phone) stays on ``clinics``."""

    __tablename__ = "clinic_settings"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    clinic_id = Column(UUID(as_uuid=True), ForeignKey("clinics.id", ondelete="CASCADE"), nullable=False, unique=True)

    currency = Column(String(3), nullable=False, default="PKR", server_default="PKR")
    timezone = Column(String(50), nullable=False, default="Asia/Karachi", server_default="Asia/Karachi")
    working_hours = Column(JSON().with_variant(JSONB(), "postgresql"), nullable=False, default=default_working_hours)
    default_slot_min = Column(Integer, nullable=False, default=30, server_default="30")

    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))