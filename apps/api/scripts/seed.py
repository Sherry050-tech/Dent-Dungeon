"""Create (or remove) DEMO data for development, so you always have logins you know.

Run from apps/api with your venv active:

    python -m scripts.seed            create the demo clinics and users (asks before writing)
    python -m scripts.seed --yes      same, without asking
    python -m scripts.seed --remove   delete ONLY the demo clinics and users again

It is safe to run twice: anything that already exists is skipped. All data here is fake.
The demo accounts share a known password, so remove them (--remove) before real clinics use
this database.
"""
import argparse
import sys

from sqlalchemy import delete, func, select
from sqlalchemy.engine import make_url
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.database import SessionLocal
from app.core.security import hash_password
from app.models.core import Clinic, ClinicSettings, User, UserRole

DEMO_PASSWORD = "Demo-Pass-123"

DEMO_CLINICS = [
    {
        "name": "Bright Smile Dental (Demo)",
        "address": "12 Mall Road, Lahore",
        "phone": "042-1234567",
        "preferences": {"currency": "PKR", "timezone": "Asia/Karachi", "default_slot_min": 30},
        "users": [
            {"email": "demo.owner@example.com", "first_name": "Sara", "last_name": "Ahmed",
             "role": UserRole.admin, "is_practitioner": True},
            {"email": "demo.doctor@example.com", "first_name": "Imran", "last_name": "Raza",
             "role": UserRole.doctor, "is_practitioner": False},
            {"email": "demo.reception@example.com", "first_name": "Hina", "last_name": "Shah",
             "role": UserRole.receptionist, "is_practitioner": False},
        ],
    },
    {
        "name": "Smile Care Clinic (Demo)",
        "address": "5 Garden Town, Karachi",
        "phone": "021-7654321",
        "preferences": {"currency": "PKR", "timezone": "Asia/Karachi", "default_slot_min": 20},
        "users": [
            {"email": "demo.owner2@example.com", "first_name": "Omar", "last_name": "Khan",
             "role": UserRole.admin, "is_practitioner": False},
            {"email": "demo.doctor2@example.com", "first_name": "Zainab", "last_name": "Iqbal",
             "role": UserRole.doctor, "is_practitioner": False},
        ],
    },
]

DEMO_EMAILS = [u["email"] for clinic in DEMO_CLINICS for u in clinic["users"]]


def seed(db: Session) -> dict:
    """Create the demo clinics and users that do not exist yet. Returns what was created."""
    created = {"clinics": [], "users": [], "skipped": []}
    password_hash = hash_password(DEMO_PASSWORD)  # one hash is enough for all demo users

    for spec in DEMO_CLINICS:
        owner_email = spec["users"][0]["email"]
        existing_owner = db.scalar(select(User).where(User.email == owner_email))
        if existing_owner is not None:
            clinic = db.get(Clinic, existing_owner.clinic_id)
        else:
            clinic = Clinic(name=spec["name"], address=spec["address"], phone=spec["phone"])
            db.add(clinic)
            db.flush()
            created["clinics"].append(spec["name"])

        for u in spec["users"]:
            if db.scalar(select(User.id).where(User.email == u["email"])) is not None:
                created["skipped"].append(u["email"])
                continue
            db.add(User(clinic_id=clinic.id, email=u["email"], hashed_password=password_hash,
                        first_name=u["first_name"], last_name=u["last_name"], role=u["role"],
                        is_practitioner=u["is_practitioner"], is_active=True))
            created["users"].append(u["email"])

        if db.scalar(select(ClinicSettings.id).where(ClinicSettings.clinic_id == clinic.id)) is None:
            db.add(ClinicSettings(clinic_id=clinic.id, **spec["preferences"]))

    db.commit()
    return created


def remove(db: Session) -> dict:
    """Delete the demo users and their clinics. A clinic that also has a real user is left alone."""
    removed = {"clinics": 0, "users": 0, "kept": []}
    clinic_ids = set(db.scalars(select(User.clinic_id).where(User.email.in_(DEMO_EMAILS))).all())

    for clinic_id in clinic_ids:
        real_users = db.scalar(
            select(func.count()).select_from(User).where(User.clinic_id == clinic_id, User.email.not_in(DEMO_EMAILS))
        )
        if real_users:
            name = db.scalar(select(Clinic.name).where(Clinic.id == clinic_id))
            removed["kept"].append(f"{name} (has {real_users} non-demo user(s); only its demo users were removed)")
            result = db.execute(delete(User).where(User.clinic_id == clinic_id, User.email.in_(DEMO_EMAILS)))
            removed["users"] += result.rowcount
            continue
        db.execute(delete(ClinicSettings).where(ClinicSettings.clinic_id == clinic_id))
        removed["users"] += db.execute(delete(User).where(User.clinic_id == clinic_id)).rowcount
        db.execute(delete(Clinic).where(Clinic.id == clinic_id))
        removed["clinics"] += 1

    db.commit()
    return removed


def _target() -> str:
    url = make_url(settings.database_url)
    return f"{url.host or 'local file'} / database '{url.database}'"


def main(argv=None, session_factory=SessionLocal, input_fn=input) -> int:
    parser = argparse.ArgumentParser(description="Create or remove demo data (fake data only).")
    parser.add_argument("--remove", action="store_true", help="delete the demo clinics and users")
    parser.add_argument("--yes", action="store_true", help="do not ask for confirmation")
    args = parser.parse_args(argv)

    action = "REMOVE the demo data from" if args.remove else "write demo data into"
    print(f"About to {action}: {_target()}")
    if not args.yes and input_fn("Type 'yes' to continue: ").strip().lower() != "yes":
        print("Cancelled. Nothing was changed.")
        return 1

    with session_factory() as db:
        if args.remove:
            result = remove(db)
            print(f"Removed {result['users']} user(s) and {result['clinics']} clinic(s).")
            for note in result["kept"]:
                print(f"  kept: {note}")
            return 0

        result = seed(db)
        print(f"Created {len(result['clinics'])} clinic(s) and {len(result['users'])} user(s); "
              f"skipped {len(result['skipped'])} that already existed.\n")

    print(f"Demo logins (password for all of them: {DEMO_PASSWORD})")
    for spec in DEMO_CLINICS:
        print(f"\n  {spec['name']}")
        for u in spec["users"]:
            flag = " + treats patients" if u["is_practitioner"] else ""
            print(f"    {u['role'].value:<13}{u['email']}{flag}")
    return 0


if __name__ == "__main__":
    sys.exit(main())