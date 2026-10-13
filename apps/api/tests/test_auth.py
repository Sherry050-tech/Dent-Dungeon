import uuid
from datetime import timedelta

import jwt
import pytest
from fastapi import Depends, FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import func, select

from app.api.deps import get_current_user, require_admin, require_roles
from app.core import security
from app.core.config import settings
from app.core.database import get_db
from app.core.errors import install_error_handlers
from app.models.core import Clinic, User, UserRole

PASSWORD = "correct-horse-battery"


def register(client, email="sara@example.com", clinic="Bright Smile Dental", **overrides):
    body = {"clinic_name": clinic, "first_name": "Sara", "last_name": "Ahmed",
            "email": email, "password": PASSWORD, "is_practitioner": True}
    body.update(overrides)
    return client.post("/api/v1/auth/register", json=body)


def login(client, email="sara@example.com", password=PASSWORD):
    return client.post("/api/v1/auth/login", json={"email": email, "password": password})


def bearer(token):
    return {"Authorization": f"Bearer {token}"}


def add_user(db, clinic_id, email, role=UserRole.doctor, active=True, password=PASSWORD):
    user = User(clinic_id=clinic_id, email=email, hashed_password=security.hash_password(password),
                first_name="Imran", last_name="Raza", role=role, is_practitioner=False, is_active=active)
    db.add(user)
    db.commit()
    return user


# ------------------------------------------------------------------ register

def test_register_creates_clinic_and_admin_and_logs_in(client, db):
    r = register(client)
    assert r.status_code == 201
    body = r.json()
    assert body["token_type"] == "bearer" and body["expires_in"] == 3600
    assert body["user"]["role"] == "admin" and body["user"]["is_practitioner"] is True
    assert body["user"]["is_active"] is True
    assert body["clinic"]["name"] == "Bright Smile Dental"
    assert body["user"]["clinic_id"] == body["clinic"]["id"]
    assert body["user"]["first_name"] == "Sara" and body["user"]["last_name"] == "Ahmed"
    # the returned token works straight away
    assert client.get("/api/v1/auth/me", headers=bearer(body["access_token"])).status_code == 200


def test_register_never_exposes_or_stores_the_plain_password(client, db):
    r = register(client)
    assert "password" not in r.text.lower().replace("password_", "")  # no password field in the response
    stored = db.scalar(select(User.hashed_password))
    assert stored.startswith("$argon2") and PASSWORD not in stored


def test_register_normalizes_email_and_trims_names(client, db):
    r = register(client, email="  Sara.Ahmed@Example.COM ".strip(), first_name="  Sara ", clinic="  Bright Smile  ")
    assert r.status_code == 201
    assert r.json()["user"]["email"] == "sara.ahmed@example.com"
    assert r.json()["user"]["first_name"] == "Sara" and r.json()["clinic"]["name"] == "Bright Smile"


def test_is_practitioner_defaults_to_false(client):
    body = {"clinic_name": "Clinic", "first_name": "A", "last_name": "B", "email": "a@example.com", "password": PASSWORD}
    assert client.post("/api/v1/auth/register", json=body).json()["user"]["is_practitioner"] is False


def test_duplicate_email_is_rejected_case_insensitively_and_leaves_no_orphan_clinic(client, db):
    assert register(client, email="sara@example.com").status_code == 201
    r = register(client, email="SARA@example.com", clinic="Another Clinic")
    assert r.status_code == 409 and r.json()["code"] == "EMAIL_TAKEN"
    assert "email" in r.json()["fields"]
    assert db.scalar(select(func.count()).select_from(Clinic)) == 1
    assert db.scalar(select(func.count()).select_from(User)) == 1


def test_every_registration_creates_a_separate_clinic(client):
    a = register(client, email="a@example.com", clinic="Clinic A").json()
    b = register(client, email="b@example.com", clinic="Clinic B").json()
    assert a["clinic"]["id"] != b["clinic"]["id"]
    assert a["user"]["role"] == "admin" and b["user"]["role"] == "admin"


def test_register_cannot_be_used_to_join_an_existing_clinic(client):
    a = register(client, email="a@example.com", clinic="Clinic A").json()
    r = register(client, email="evil@example.com", clinic="Evil Clinic", clinic_id=a["clinic"]["id"])
    assert r.status_code == 201
    assert r.json()["clinic"]["id"] != a["clinic"]["id"]  # the client-supplied clinic_id was ignored


@pytest.mark.parametrize("overrides, field", [
    ({"password": "short"}, "password"),
    ({"password": "x" * 129}, "password"),
    ({"email": "not-an-email"}, "email"),
    ({"clinic_name": " "}, "clinic_name"),
    ({"clinic_name": "A"}, "clinic_name"),
    ({"first_name": ""}, "first_name"),
    ({"last_name": "   "}, "last_name"),
    ({"first_name": "x" * 81}, "first_name"),
])
def test_register_validation_errors_use_the_documented_format(client, overrides, field):
    r = register(client, **overrides)
    assert r.status_code == 422
    body = r.json()
    assert body["code"] == "VALIDATION_ERROR" and isinstance(body["fields"], dict)
    assert field in body["fields"] and isinstance(body["fields"][field], str)


def test_missing_fields_are_reported_per_field(client):
    r = client.post("/api/v1/auth/register", json={})
    assert r.status_code == 422
    assert set(r.json()["fields"]) == {"clinic_name", "first_name", "last_name", "email", "password"}
    assert r.json()["fields"]["email"] == "This field is required"


def test_malformed_json_is_a_clean_422_not_a_500(client):
    r = client.post("/api/v1/auth/register", content="{not json", headers={"Content-Type": "application/json"})
    assert r.status_code == 422 and r.json()["code"] == "VALIDATION_ERROR"


# ---------------------------------------------------------------------- login

def test_login_succeeds_and_records_last_login(client, db):
    register(client)
    r = login(client)
    assert r.status_code == 200
    body = r.json()
    assert {"access_token", "refresh_token", "user", "clinic", "expires_in"} <= set(body)
    assert body["user"]["email"] == "sara@example.com"
    db.expire_all()
    assert db.scalar(select(User.last_login_at)) is not None


def test_login_email_is_case_insensitive(client):
    register(client)
    assert login(client, email="  SARA@Example.com ").status_code == 200


def test_unknown_email_and_wrong_password_look_identical(client):
    register(client)
    wrong_pw = login(client, password="not-the-password")
    no_user = login(client, email="nobody@example.com")
    assert wrong_pw.status_code == no_user.status_code == 401
    assert wrong_pw.json() == no_user.json()
    assert wrong_pw.json()["code"] == "INVALID_CREDENTIALS"


def test_inactive_account_with_correct_password_is_403(client, db):
    register(client)
    user = db.scalar(select(User)); user.is_active = False; db.commit()
    r = login(client)
    assert r.status_code == 403 and r.json()["code"] == "ACCOUNT_INACTIVE"


def test_inactive_account_with_wrong_password_does_not_reveal_it_exists(client, db):
    register(client)
    user = db.scalar(select(User)); user.is_active = False; db.commit()
    r = login(client, password="wrong-password")
    assert r.status_code == 401 and r.json()["code"] == "INVALID_CREDENTIALS"


def test_login_accepts_addresses_the_register_form_would_reject(client, db):
    # seeded or imported accounts may use addresses like admin@dentdungeon.test
    clinic = Clinic(name="Seeded"); db.add(clinic); db.commit()
    add_user(db, clinic.id, "admin@dentdungeon.test", role=UserRole.admin)
    assert login(client, email="admin@dentdungeon.test").status_code == 200


# ------------------------------------------------------------------------- me

def test_me_returns_user_and_clinic(client):
    body = register(client).json()
    r = client.get("/api/v1/auth/me", headers=bearer(body["access_token"]))
    assert r.status_code == 200
    assert r.json()["user"]["email"] == "sara@example.com"
    assert r.json()["clinic"]["id"] == body["clinic"]["id"]


def test_each_user_only_sees_their_own_clinic(client):
    a = register(client, email="a@example.com", clinic="Clinic A").json()
    b = register(client, email="b@example.com", clinic="Clinic B").json()
    me_a = client.get("/api/v1/auth/me", headers=bearer(a["access_token"])).json()
    me_b = client.get("/api/v1/auth/me", headers=bearer(b["access_token"])).json()
    assert me_a["clinic"]["name"] == "Clinic A" and me_b["clinic"]["name"] == "Clinic B"


def test_me_without_a_token_is_401(client):
    r = client.get("/api/v1/auth/me")
    assert r.status_code == 401 and r.json()["code"] == "NOT_AUTHENTICATED"
    assert r.headers["www-authenticate"] == "Bearer"


@pytest.mark.parametrize("header", ["Bearer garbage", "Bearer ", "Basic abc", "Token abc", "Bearer a.b.c"])
def test_me_with_a_bad_authorization_header_is_401(client, header):
    r = client.get("/api/v1/auth/me", headers={"Authorization": header})
    assert r.status_code == 401 and r.json()["code"] == "NOT_AUTHENTICATED"


def test_refresh_token_cannot_be_used_as_an_access_token(client):
    body = register(client).json()
    r = client.get("/api/v1/auth/me", headers=bearer(body["refresh_token"]))
    assert r.status_code == 401 and r.json()["code"] == "NOT_AUTHENTICATED"


def test_expired_access_token_is_reported_so_the_ui_can_refresh(client):
    body = register(client).json()
    expired = security.create_access_token(body["user"]["id"], timedelta(minutes=-5))
    r = client.get("/api/v1/auth/me", headers=bearer(expired))
    assert r.status_code == 401 and r.json()["code"] == "TOKEN_EXPIRED"


def test_token_signed_with_another_secret_is_rejected(client):
    body = register(client).json()
    forged = jwt.encode({"sub": body["user"]["id"], "type": "access", "exp": 9999999999}, "other-secret-" + "x" * 40, algorithm="HS256")
    assert client.get("/api/v1/auth/me", headers=bearer(forged)).status_code == 401


def test_unsigned_alg_none_token_is_rejected(client):
    body = register(client).json()
    unsigned = jwt.encode({"sub": body["user"]["id"], "type": "access", "exp": 9999999999}, key=None, algorithm="none")
    assert client.get("/api/v1/auth/me", headers=bearer(unsigned)).status_code == 401


def test_token_without_expiry_is_rejected(client):
    body = register(client).json()
    no_exp = jwt.encode({"sub": body["user"]["id"], "type": "access"}, settings.secret_key, algorithm="HS256")
    assert client.get("/api/v1/auth/me", headers=bearer(no_exp)).status_code == 401


def test_token_for_a_user_that_does_not_exist_is_rejected(client):
    ghost = security.create_access_token(uuid.uuid4())
    assert client.get("/api/v1/auth/me", headers=bearer(ghost)).status_code == 401


def test_token_with_a_malformed_subject_is_rejected(client):
    bad = security.create_access_token("not-a-uuid")
    assert client.get("/api/v1/auth/me", headers=bearer(bad)).status_code == 401


def test_deactivating_a_user_locks_them_out_immediately(client, db):
    token = register(client).json()["access_token"]
    assert client.get("/api/v1/auth/me", headers=bearer(token)).status_code == 200
    user = db.scalar(select(User)); user.is_active = False; db.commit()
    assert client.get("/api/v1/auth/me", headers=bearer(token)).status_code == 401


# -------------------------------------------------------------------- refresh

def test_refresh_returns_a_working_access_token(client):
    body = register(client).json()
    r = client.post("/api/v1/auth/refresh", json={"refresh_token": body["refresh_token"]})
    assert r.status_code == 200 and r.json()["expires_in"] == 3600
    assert client.get("/api/v1/auth/me", headers=bearer(r.json()["access_token"])).status_code == 200


def test_access_token_cannot_be_used_to_refresh(client):
    body = register(client).json()
    r = client.post("/api/v1/auth/refresh", json={"refresh_token": body["access_token"]})
    assert r.status_code == 401 and r.json()["code"] == "NOT_AUTHENTICATED"


def test_expired_refresh_token_is_token_expired(client):
    body = register(client).json()
    expired = security.create_refresh_token(body["user"]["id"], timedelta(days=-1))
    r = client.post("/api/v1/auth/refresh", json={"refresh_token": expired})
    assert r.status_code == 401 and r.json()["code"] == "TOKEN_EXPIRED"


def test_refresh_fails_for_a_deactivated_user(client, db):
    body = register(client).json()
    user = db.scalar(select(User)); user.is_active = False; db.commit()
    assert client.post("/api/v1/auth/refresh", json={"refresh_token": body["refresh_token"]}).status_code == 401


# ------------------------------------------------------------ change password

def test_change_password_end_to_end(client):
    token = register(client).json()["access_token"]
    r = client.post("/api/v1/auth/change-password", headers=bearer(token),
                    json={"current_password": PASSWORD, "new_password": "a-brand-new-password"})
    assert r.status_code == 204 and r.content == b""
    assert login(client, password=PASSWORD).status_code == 401
    assert login(client, password="a-brand-new-password").status_code == 200


def test_change_password_rejects_the_wrong_current_password(client):
    token = register(client).json()["access_token"]
    r = client.post("/api/v1/auth/change-password", headers=bearer(token),
                    json={"current_password": "wrong", "new_password": "a-brand-new-password"})
    assert r.status_code == 400 and r.json()["code"] == "WRONG_PASSWORD"


def test_change_password_validates_the_new_password(client):
    token = register(client).json()["access_token"]
    short = client.post("/api/v1/auth/change-password", headers=bearer(token), json={"current_password": PASSWORD, "new_password": "short"})
    same = client.post("/api/v1/auth/change-password", headers=bearer(token), json={"current_password": PASSWORD, "new_password": PASSWORD})
    assert short.status_code == 422 and "new_password" in short.json()["fields"]
    assert same.status_code == 422 and "new_password" in same.json()["fields"]


def test_change_password_requires_login(client):
    r = client.post("/api/v1/auth/change-password", json={"current_password": "a", "new_password": "b" * 10})
    assert r.status_code == 401


# ---------------------------------------------------------- roles and errors

@pytest.fixture()
def guarded_client(engine):
    """A tiny app with routes protected by the role dependencies, to test them in isolation."""
    from sqlalchemy.orm import sessionmaker
    factory = sessionmaker(bind=engine, autoflush=False)
    guarded = FastAPI()
    install_error_handlers(guarded)

    def override_get_db():
        s = factory()
        try:
            yield s
        finally:
            s.close()

    guarded.dependency_overrides[get_db] = override_get_db
    guarded.get("/admin-only")(lambda user=Depends(require_admin): {"role": user.role.value})
    guarded.get("/staff")(lambda user=Depends(require_roles(UserRole.admin, UserRole.doctor)): {"ok": True})
    return TestClient(guarded)


def test_role_dependencies_allow_and_deny_correctly(guarded_client, db):
    clinic = Clinic(name="C"); db.add(clinic); db.commit()
    add_user(db, clinic.id, "admin@example.com", UserRole.admin)
    add_user(db, clinic.id, "doc@example.com", UserRole.doctor)
    add_user(db, clinic.id, "recep@example.com", UserRole.receptionist)
    token = lambda email: security.create_access_token(db.scalar(select(User.id).where(User.email == email)))

    assert guarded_client.get("/admin-only", headers=bearer(token("admin@example.com"))).status_code == 200
    denied = guarded_client.get("/admin-only", headers=bearer(token("doc@example.com")))
    assert denied.status_code == 403 and denied.json()["code"] == "FORBIDDEN"
    assert guarded_client.get("/staff", headers=bearer(token("doc@example.com"))).status_code == 200
    assert guarded_client.get("/staff", headers=bearer(token("recep@example.com"))).status_code == 403
    assert guarded_client.get("/admin-only").status_code == 401


def test_unknown_routes_and_wrong_methods_use_the_error_format(client):
    nf = client.get("/api/v1/nope")
    assert nf.status_code == 404 and nf.json() == {"detail": "Not Found", "code": "NOT_FOUND"}
    mna = client.get("/api/v1/auth/login")
    assert mna.status_code == 405 and mna.json()["code"] == "METHOD_NOT_ALLOWED"


def test_health_still_works(client):
    assert client.get("/api/v1/health").json() == {"status": "ok"}


# ------------------------------------------------------------ security module

def test_password_hashes_are_salted_and_verify_correctly():
    h1, h2 = security.hash_password(PASSWORD), security.hash_password(PASSWORD)
    assert h1 != h2 and security.verify_password(PASSWORD, h1) and not security.verify_password("nope", h1)


def test_verify_password_never_raises_on_garbage_hashes():
    assert security.verify_password("x", "not-a-real-hash") is False
    assert security.verify_password("x", "") is False


def test_unknown_email_still_burns_a_password_hash_so_timing_does_not_reveal_accounts(client, monkeypatch):
    from app.services import auth_service
    calls = []
    monkeypatch.setattr(auth_service, "verify_dummy_password", lambda pw: calls.append(pw))
    register(client)
    login(client, email="nobody@example.com")
    assert calls == [PASSWORD]          # unknown email: a dummy hash was verified
    calls.clear()
    login(client, password="wrong-password")
    login(client)
    assert calls == []                   # known email: the real hash is verified instead


def test_validation_messages_are_readable_by_people(client):
    r = register(client, email="nope", first_name="", password="short", clinic=" ")
    fields = r.json()["fields"]
    assert fields["email"] == "Enter a valid email address"
    assert fields["first_name"] == "This field is required"
    assert fields["password"] == "Must be at least 8 characters"
    assert fields["clinic_name"] == "Must be at least 2 characters"