import pytest
from helpers import auth, login_token, register_clinic
from sqlalchemy import func, select
from sqlalchemy.orm import sessionmaker

from app.models.core import Clinic, ClinicSettings, User, UserRole
from scripts.seed import DEMO_CLINICS, DEMO_EMAILS, DEMO_PASSWORD, main, remove, seed


def count(db, model):
    return db.scalar(select(func.count()).select_from(model))


def test_seed_creates_the_demo_clinics_users_and_preferences(db):
    result = seed(db)
    assert count(db, Clinic) == 2 and count(db, User) == 5 and count(db, ClinicSettings) == 2
    assert len(result["clinics"]) == 2 and len(result["users"]) == 5 and result["skipped"] == []
    owner = db.scalar(select(User).where(User.email == "demo.owner@example.com"))
    assert owner.role == UserRole.admin and owner.is_practitioner is True and owner.is_active is True
    assert owner.hashed_password.startswith("$argon2") and DEMO_PASSWORD not in owner.hashed_password
    assert db.scalar(select(User.role).where(User.email == "demo.reception@example.com")) == UserRole.receptionist


def test_seeding_twice_changes_nothing(db):
    seed(db)
    again = seed(db)
    assert count(db, Clinic) == 2 and count(db, User) == 5 and count(db, ClinicSettings) == 2
    assert again["clinics"] == [] and again["users"] == [] and len(again["skipped"]) == 5


def test_seed_never_overwrites_an_existing_account(db, client):
    seed(db)
    token = login_token(client, "demo.owner@example.com", DEMO_PASSWORD)
    client.post("/api/v1/auth/change-password", headers=auth(token),
                json={"current_password": DEMO_PASSWORD, "new_password": "my-own-new-password"})
    seed(db)  # must not reset the password back
    assert client.post("/api/v1/auth/login", json={"email": "demo.owner@example.com", "password": DEMO_PASSWORD}).status_code == 401
    assert login_token(client, "demo.owner@example.com", "my-own-new-password")


def test_every_demo_account_can_log_in_and_sees_only_its_own_clinic(db, client):
    seed(db)
    names = {}
    for spec in DEMO_CLINICS:
        for u in spec["users"]:
            r = client.post("/api/v1/auth/login", json={"email": u["email"], "password": DEMO_PASSWORD})
            assert r.status_code == 200, u["email"]
            assert r.json()["user"]["role"] == u["role"].value
            names[u["email"]] = r.json()["clinic"]["name"]
    assert {names["demo.owner@example.com"], names["demo.doctor@example.com"], names["demo.reception@example.com"]} == {"Bright Smile Dental (Demo)"}
    assert {names["demo.owner2@example.com"], names["demo.doctor2@example.com"]} == {"Smile Care Clinic (Demo)"}


def test_demo_data_exercises_the_staff_and_isolation_rules(db, client):
    seed(db)
    owner1 = login_token(client, "demo.owner@example.com", DEMO_PASSWORD)
    owner2 = login_token(client, "demo.owner2@example.com", DEMO_PASSWORD)
    staff1 = {u["email"] for u in client.get("/api/v1/users", headers=auth(owner1)).json()["items"]}
    staff2 = {u["email"] for u in client.get("/api/v1/users", headers=auth(owner2)).json()["items"]}
    assert staff1 == {"demo.owner@example.com", "demo.doctor@example.com", "demo.reception@example.com"}
    assert staff2 == {"demo.owner2@example.com", "demo.doctor2@example.com"}
    # the solo-style owner (is_practitioner) and the doctor are the treating clinicians of clinic 1
    doctors = {u["email"] for u in client.get("/api/v1/users/doctors", headers=auth(owner1)).json()["items"]}
    assert doctors == {"demo.owner@example.com", "demo.doctor@example.com"}
    # clinic 2's owner does not treat patients, so only the doctor is listed
    assert {u["email"] for u in client.get("/api/v1/users/doctors", headers=auth(owner2)).json()["items"]} == {"demo.doctor2@example.com"}
    prefs = client.get("/api/v1/settings/clinic", headers=auth(owner2)).json()
    assert prefs["clinic"]["name"] == "Smile Care Clinic (Demo)" and prefs["preferences"]["default_slot_min"] == 20


def test_remove_deletes_only_the_demo_data(db, client):
    seed(db)
    real = register_clinic(client, "real.owner@example.com", "A Real Clinic")
    result = remove(db)
    assert result == {"clinics": 2, "users": 5, "kept": []}
    assert count(db, Clinic) == 1 and count(db, User) == 1 and count(db, ClinicSettings) == 0
    assert client.get("/api/v1/auth/me", headers=auth(real["access_token"])).status_code == 200  # untouched
    assert remove(db) == {"clinics": 0, "users": 0, "kept": []}  # running it again is harmless


def test_remove_never_deletes_a_clinic_that_has_a_real_user(db, client):
    seed(db)
    owner = login_token(client, "demo.owner@example.com", DEMO_PASSWORD)
    client.post("/api/v1/users", headers=auth(owner), json={
        "first_name": "Real", "last_name": "Person", "email": "real.person@example.com",
        "temporary_password": "temp-password-1", "role": "doctor"})
    result = remove(db)
    assert result["clinics"] == 1 and len(result["kept"]) == 1  # only the other demo clinic was deleted
    survivors = set(db.scalars(select(User.email)).all())
    assert survivors == {"real.person@example.com"}  # demo users gone, the real one kept
    assert count(db, Clinic) == 1


def test_cli_asks_before_writing_and_cancel_changes_nothing(engine, db, capsys):
    factory = sessionmaker(bind=engine)
    code = main([], session_factory=factory, input_fn=lambda prompt: "no")
    assert code == 1 and "Cancelled" in capsys.readouterr().out
    assert count(db, User) == 0
    code = main([], session_factory=factory, input_fn=lambda prompt: "yes")
    out = capsys.readouterr().out
    assert code == 0 and count(db, User) == 5
    assert DEMO_PASSWORD in out and "demo.owner@example.com" in out and "treats patients" in out


def test_cli_yes_flag_and_remove_flag(engine, db, capsys):
    factory = sessionmaker(bind=engine)
    assert main(["--yes"], session_factory=factory, input_fn=lambda p: pytest.fail("must not ask")) == 0
    assert count(db, User) == 5
    assert main(["--remove", "--yes"], session_factory=factory) == 0
    assert "Removed 5 user(s) and 2 clinic(s)" in capsys.readouterr().out
    assert count(db, User) == 0


def test_demo_emails_are_all_unique_example_addresses():
    assert len(DEMO_EMAILS) == len(set(DEMO_EMAILS)) == 5
    assert all(e.endswith("@example.com") for e in DEMO_EMAILS)