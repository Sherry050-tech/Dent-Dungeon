import uuid

import pytest
from helpers import PASSWORD, TEMP_PASSWORD, auth, create_staff, login_token, register_clinic

URL = "/api/v1/users"


@pytest.fixture()
def clinic_a(client):
    return register_clinic(client, "owner-a@example.com", "Clinic A")


@pytest.fixture()
def clinic_b(client):
    return register_clinic(client, "owner-b@example.com", "Clinic B")


# ----------------------------------------------------------------- create

def test_admin_creates_staff_who_can_then_log_in(client, clinic_a):
    created = create_staff(client, clinic_a["access_token"], "Imran@Example.com", role="doctor")
    assert created["email"] == "imran@example.com" and created["role"] == "doctor"
    assert created["is_active"] is True and created["is_practitioner"] is False
    assert created["clinic_id"] == clinic_a["clinic"]["id"]
    assert "password" not in str(created).lower()
    r = client.post("/api/v1/auth/login", json={"email": "imran@example.com", "password": TEMP_PASSWORD})
    assert r.status_code == 200 and r.json()["clinic"]["id"] == clinic_a["clinic"]["id"]


def test_new_staff_always_join_the_admins_own_clinic(client, clinic_a, clinic_b):
    r = client.post(URL, headers=auth(clinic_a["access_token"]), json={
        "first_name": "Evil", "last_name": "Plan", "email": "x@example.com", "temporary_password": TEMP_PASSWORD,
        "role": "receptionist", "clinic_id": clinic_b["clinic"]["id"]})
    assert r.status_code == 201
    assert r.json()["clinic_id"] == clinic_a["clinic"]["id"]  # the client-supplied clinic_id was ignored


def test_admin_can_create_another_admin_and_a_practitioner_admin(client, clinic_a):
    created = create_staff(client, clinic_a["access_token"], "second@example.com", role="admin", is_practitioner=True)
    assert created["role"] == "admin" and created["is_practitioner"] is True


@pytest.mark.parametrize("who", ["doctor", "receptionist"])
def test_only_admins_can_manage_staff(client, clinic_a, who):
    token = login_token(client, create_staff(client, clinic_a["access_token"], f"{who}@example.com", role=who)["email"])
    other = create_staff(client, clinic_a["access_token"], "other@example.com")
    assert client.get(URL, headers=auth(token)).status_code == 403
    assert client.post(URL, headers=auth(token), json={"first_name": "A", "last_name": "B", "email": "z@example.com",
                                                      "temporary_password": TEMP_PASSWORD, "role": "doctor"}).status_code == 403
    assert client.patch(f"{URL}/{other['id']}", headers=auth(token), json={"is_active": False}).status_code == 403
    assert client.get(URL, headers=auth(token)).json()["code"] == "FORBIDDEN"


def test_staff_endpoints_require_login(client, clinic_a):
    assert client.get(URL).status_code == 401
    assert client.post(URL, json={}).status_code == 401
    assert client.get(f"{URL}/doctors").status_code == 401
    assert client.patch(f"{URL}/{uuid.uuid4()}", json={}).status_code == 401


def test_duplicate_email_is_rejected_even_across_clinics(client, clinic_a, clinic_b):
    create_staff(client, clinic_a["access_token"], "dup@example.com")
    for token in (clinic_a["access_token"], clinic_b["access_token"]):
        r = client.post(URL, headers=auth(token), json={"first_name": "A", "last_name": "B", "email": "DUP@example.com",
                                                       "temporary_password": TEMP_PASSWORD, "role": "doctor"})
        assert r.status_code == 409 and r.json()["code"] == "EMAIL_TAKEN" and "email" in r.json()["fields"]


@pytest.mark.parametrize("override, field", [
    ({"email": "nope"}, "email"),
    ({"temporary_password": "short"}, "temporary_password"),
    ({"role": "owner"}, "role"),
    ({"first_name": ""}, "first_name"),
    ({"last_name": "  "}, "last_name"),
])
def test_create_validation_errors_name_the_field(client, clinic_a, override, field):
    body = {"first_name": "A", "last_name": "B", "email": "ok@example.com", "temporary_password": TEMP_PASSWORD, "role": "doctor"}
    body.update(override)
    r = client.post(URL, headers=auth(clinic_a["access_token"]), json=body)
    assert r.status_code == 422 and r.json()["code"] == "VALIDATION_ERROR" and field in r.json()["fields"]


# ------------------------------------------------------------------- list

def test_list_returns_only_my_clinics_staff_in_the_standard_envelope(client, clinic_a, clinic_b):
    create_staff(client, clinic_a["access_token"], "a1@example.com", first_name="Zara")
    create_staff(client, clinic_a["access_token"], "a2@example.com", first_name="Amir")
    create_staff(client, clinic_b["access_token"], "b1@example.com", first_name="Bilal")
    body = client.get(URL, headers=auth(clinic_a["access_token"])).json()
    assert set(body) == {"items", "total", "page", "limit"}
    assert body["total"] == 3 and body["page"] == 1 and body["limit"] == 20
    emails = {u["email"] for u in body["items"]}
    assert emails == {"owner-a@example.com", "a1@example.com", "a2@example.com"}
    assert [u["first_name"] for u in body["items"]] == sorted(u["first_name"] for u in body["items"])  # alphabetical
    assert all(u["clinic_id"] == clinic_a["clinic"]["id"] for u in body["items"])
    assert "hashed_password" not in str(body)


def test_list_filters_and_pagination(client, clinic_a):
    tok = clinic_a["access_token"]
    for i in range(5):
        create_staff(client, tok, f"doc{i}@example.com", role="doctor", first_name=f"Doc{i}")
    create_staff(client, tok, "rec@example.com", role="receptionist")
    assert client.get(URL, params={"role": "doctor"}, headers=auth(tok)).json()["total"] == 5
    assert client.get(URL, params={"role": "receptionist"}, headers=auth(tok)).json()["total"] == 1
    page2 = client.get(URL, params={"limit": 2, "page": 2}, headers=auth(tok)).json()
    assert page2["page"] == 2 and page2["limit"] == 2 and len(page2["items"]) == 2 and page2["total"] == 7
    last = client.get(URL, params={"limit": 4, "page": 2}, headers=auth(tok)).json()
    assert len(last["items"]) == 3
    # deactivate one and filter on it
    victim = client.get(URL, params={"role": "receptionist"}, headers=auth(tok)).json()["items"][0]
    client.patch(f"{URL}/{victim['id']}", headers=auth(tok), json={"is_active": False})
    assert client.get(URL, params={"is_active": "false"}, headers=auth(tok)).json()["total"] == 1
    assert client.get(URL, params={"is_active": "true"}, headers=auth(tok)).json()["total"] == 6


@pytest.mark.parametrize("params", [{"limit": 101}, {"limit": 0}, {"page": 0}, {"role": "owner"}])
def test_list_rejects_bad_query_parameters(client, clinic_a, params):
    r = client.get(URL, params=params, headers=auth(clinic_a["access_token"]))
    assert r.status_code == 422 and r.json()["code"] == "VALIDATION_ERROR"


# -------------------------------------------------------------------- get

def test_admin_gets_a_user_and_other_clinics_users_are_404(client, clinic_a, clinic_b):
    mine = create_staff(client, clinic_a["access_token"], "mine@example.com")
    theirs = create_staff(client, clinic_b["access_token"], "theirs@example.com")
    assert client.get(f"{URL}/{mine['id']}", headers=auth(clinic_a["access_token"])).json()["email"] == "mine@example.com"
    cross = client.get(f"{URL}/{theirs['id']}", headers=auth(clinic_a["access_token"]))
    missing = client.get(f"{URL}/{uuid.uuid4()}", headers=auth(clinic_a["access_token"]))
    assert cross.status_code == missing.status_code == 404
    assert cross.json() == missing.json() and cross.json()["code"] == "NOT_FOUND"  # indistinguishable: nothing leaks


def test_a_non_admin_can_read_only_themselves(client, clinic_a):
    me = create_staff(client, clinic_a["access_token"], "me@example.com", role="doctor")
    other = create_staff(client, clinic_a["access_token"], "other@example.com", role="doctor")
    token = login_token(client, "me@example.com")
    assert client.get(f"{URL}/{me['id']}", headers=auth(token)).status_code == 200
    assert client.get(f"{URL}/{other['id']}", headers=auth(token)).status_code == 403


def test_invalid_user_id_is_a_clean_422(client, clinic_a):
    r = client.get(f"{URL}/not-a-uuid", headers=auth(clinic_a["access_token"]))
    assert r.status_code == 422 and r.json()["code"] == "VALIDATION_ERROR"


# ------------------------------------------------------------------ patch

def test_admin_updates_names_role_and_practitioner_flag(client, clinic_a):
    tok = clinic_a["access_token"]
    u = create_staff(client, tok, "up@example.com", role="receptionist")
    r = client.patch(f"{URL}/{u['id']}", headers=auth(tok),
                     json={"first_name": "  Hira ", "last_name": "Malik", "role": "doctor", "is_practitioner": True})
    assert r.status_code == 200
    got = client.get(f"{URL}/{u['id']}", headers=auth(tok)).json()
    assert (got["first_name"], got["last_name"], got["role"], got["is_practitioner"]) == ("Hira", "Malik", "doctor", True)
    assert got["email"] == "up@example.com"  # untouched


def test_patch_only_changes_the_fields_that_were_sent(client, clinic_a):
    tok = clinic_a["access_token"]
    u = create_staff(client, tok, "partial@example.com", role="doctor", is_practitioner=True, first_name="Keep", last_name="Me")
    r = client.patch(f"{URL}/{u['id']}", headers=auth(tok), json={"last_name": "Changed"})
    assert r.json()["first_name"] == "Keep" and r.json()["last_name"] == "Changed"
    assert r.json()["role"] == "doctor" and r.json()["is_practitioner"] is True and r.json()["is_active"] is True
    assert client.patch(f"{URL}/{u['id']}", headers=auth(tok), json={}).status_code == 200  # empty patch is a no-op


def test_email_and_password_cannot_be_changed_through_patch(client, clinic_a):
    tok = clinic_a["access_token"]
    u = create_staff(client, tok, "fixed@example.com")
    r = client.patch(f"{URL}/{u['id']}", headers=auth(tok), json={"email": "new@example.com", "hashed_password": "x", "clinic_id": str(uuid.uuid4())})
    assert r.status_code == 200 and r.json()["email"] == "fixed@example.com"
    assert login_token(client, "fixed@example.com")  # the old password still works


@pytest.mark.parametrize("body", [{"first_name": None}, {"role": None}, {"is_active": None}, {"role": "owner"}, {"first_name": ""}])
def test_patch_rejects_nulls_and_bad_values(client, clinic_a, body):
    u = create_staff(client, clinic_a["access_token"], "v@example.com")
    r = client.patch(f"{URL}/{u['id']}", headers=auth(clinic_a["access_token"]), json=body)
    assert r.status_code == 422 and r.json()["code"] == "VALIDATION_ERROR"


def test_an_admin_cannot_modify_another_clinics_user(client, clinic_a, clinic_b):
    theirs = create_staff(client, clinic_b["access_token"], "theirs@example.com")
    r = client.patch(f"{URL}/{theirs['id']}", headers=auth(clinic_a["access_token"]), json={"is_active": False, "role": "admin"})
    assert r.status_code == 404
    after = client.get(f"{URL}/{theirs['id']}", headers=auth(clinic_b["access_token"])).json()
    assert after["is_active"] is True and after["role"] == "doctor"  # nothing changed


def test_deactivating_locks_the_user_out_at_once_and_reactivating_restores_access(client, clinic_a):
    tok = clinic_a["access_token"]
    u = create_staff(client, tok, "lock@example.com")
    staff_token = login_token(client, "lock@example.com")
    assert client.get("/api/v1/auth/me", headers=auth(staff_token)).status_code == 200

    client.patch(f"{URL}/{u['id']}", headers=auth(tok), json={"is_active": False})
    assert client.get("/api/v1/auth/me", headers=auth(staff_token)).status_code == 401  # existing token stops working
    r = client.post("/api/v1/auth/login", json={"email": "lock@example.com", "password": TEMP_PASSWORD})
    assert r.status_code == 403 and r.json()["code"] == "ACCOUNT_INACTIVE"

    client.patch(f"{URL}/{u['id']}", headers=auth(tok), json={"is_active": True})
    assert login_token(client, "lock@example.com")


# -------------------------------------------------------- last admin rule

def test_the_only_admin_cannot_deactivate_or_demote_themselves(client, clinic_a):
    tok, me = clinic_a["access_token"], clinic_a["user"]["id"]
    for body in ({"is_active": False}, {"role": "doctor"}, {"role": "receptionist", "is_active": False}):
        r = client.patch(f"{URL}/{me}", headers=auth(tok), json=body)
        assert r.status_code == 400 and r.json()["code"] == "LAST_ADMIN", body
    assert client.get("/api/v1/auth/me", headers=auth(tok)).json()["user"]["role"] == "admin"
    # harmless edits to themselves are still fine
    assert client.patch(f"{URL}/{me}", headers=auth(tok), json={"first_name": "Renamed", "role": "admin", "is_active": True}).status_code == 200


def test_with_two_admins_one_may_step_down_but_not_the_last(client, clinic_a):
    tok, first = clinic_a["access_token"], clinic_a["user"]["id"]
    second = create_staff(client, tok, "second-admin@example.com", role="admin")
    assert client.patch(f"{URL}/{second['id']}", headers=auth(tok), json={"role": "doctor"}).status_code == 200
    r = client.patch(f"{URL}/{first}", headers=auth(tok), json={"is_active": False})
    assert r.status_code == 400 and r.json()["code"] == "LAST_ADMIN"


def test_deactivated_admins_do_not_count_as_admins(client, clinic_a):
    tok, first = clinic_a["access_token"], clinic_a["user"]["id"]
    second = create_staff(client, tok, "ghost-admin@example.com", role="admin")
    assert client.patch(f"{URL}/{second['id']}", headers=auth(tok), json={"is_active": False}).status_code == 200
    assert client.patch(f"{URL}/{first}", headers=auth(tok), json={"role": "doctor"}).json()["code"] == "LAST_ADMIN"


def test_admins_of_other_clinics_do_not_count(client, clinic_a, clinic_b):
    r = client.patch(f"{URL}/{clinic_a['user']['id']}", headers=auth(clinic_a["access_token"]), json={"is_active": False})
    assert r.status_code == 400 and r.json()["code"] == "LAST_ADMIN"  # clinic B has an admin, but that is irrelevant


def test_non_admins_can_be_deactivated_freely(client, clinic_a):
    u = create_staff(client, clinic_a["access_token"], "free@example.com", role="doctor")
    assert client.patch(f"{URL}/{u['id']}", headers=auth(clinic_a["access_token"]), json={"is_active": False}).status_code == 200


# --------------------------------------------------------------- doctors

def test_doctors_endpoint_lists_active_practitioners_of_my_clinic_only(client, clinic_a, clinic_b):
    tok = clinic_a["access_token"]  # the owner registered with is_practitioner=True
    create_staff(client, tok, "doc@example.com", role="doctor", first_name="Doc")
    create_staff(client, tok, "rec@example.com", role="receptionist")
    create_staff(client, tok, "plain-admin@example.com", role="admin", is_practitioner=False)
    create_staff(client, tok, "dentist-rec@example.com", role="receptionist", is_practitioner=True, first_name="Dentist")
    gone = create_staff(client, tok, "gone@example.com", role="doctor")
    client.patch(f"{URL}/{gone['id']}", headers=auth(tok), json={"is_active": False})
    create_staff(client, clinic_b["access_token"], "other-doc@example.com", role="doctor")

    body = client.get(f"{URL}/doctors", headers=auth(tok)).json()
    emails = {u["email"] for u in body["items"]}
    assert emails == {"owner-a@example.com", "doc@example.com", "dentist-rec@example.com"}
    assert body["total"] == 3 and body["page"] == 1


def test_any_logged_in_role_can_list_doctors_and_the_route_is_not_swallowed_by_user_id(client, clinic_a):
    create_staff(client, clinic_a["access_token"], "front@example.com", role="receptionist")
    token = login_token(client, "front@example.com")
    r = client.get(f"{URL}/doctors", headers=auth(token))
    assert r.status_code == 200 and r.json()["total"] == 1  # the owner, a practitioner


def test_a_solo_dentist_appears_as_their_own_treating_doctor(client):
    solo = register_clinic(client, "solo@example.com", "Solo Clinic", is_practitioner=True)
    body = client.get(f"{URL}/doctors", headers=auth(solo["access_token"])).json()
    assert [u["id"] for u in body["items"]] == [solo["user"]["id"]]
    not_practitioner = register_clinic(client, "admin-only@example.com", "Office Clinic", is_practitioner=False)
    assert client.get(f"{URL}/doctors", headers=auth(not_practitioner["access_token"])).json()["items"] == []