
import pytest
from helpers import auth, create_staff, login_token, register_clinic
from sqlalchemy import func, select

from app.models.core import ClinicSettings

URL = "/api/v1/settings/clinic"


@pytest.fixture()
def clinic_a(client):
    return register_clinic(client, "owner-a@example.com", "Clinic A")


@pytest.fixture()
def clinic_b(client):
    return register_clinic(client, "owner-b@example.com", "Clinic B")


def test_first_read_creates_default_preferences_once(client, db, clinic_a):
    body = client.get(URL, headers=auth(clinic_a["access_token"])).json()
    assert body["clinic"] == {"id": clinic_a["clinic"]["id"], "name": "Clinic A", "address": None, "phone": None}
    prefs = body["preferences"]
    assert (prefs["currency"], prefs["timezone"], prefs["default_slot_min"]) == ("PKR", "Asia/Karachi", 30)
    assert prefs["working_hours"]["mon"] == ["09:00", "17:00"] and prefs["working_hours"]["sun"] is None
    assert list(prefs["working_hours"]) == ["mon", "tue", "wed", "thu", "fri", "sat", "sun"]
    client.get(URL, headers=auth(clinic_a["access_token"]))
    assert db.scalar(select(func.count()).select_from(ClinicSettings)) == 1  # not created twice


def test_every_role_can_read_but_login_is_required(client, clinic_a):
    assert client.get(URL).status_code == 401
    for role in ("doctor", "receptionist"):
        create_staff(client, clinic_a["access_token"], f"{role}@example.com", role=role)
        token = login_token(client, f"{role}@example.com")
        assert client.get(URL, headers=auth(token)).status_code == 200


def test_only_admins_can_change_settings(client, clinic_a):
    for role in ("doctor", "receptionist"):
        create_staff(client, clinic_a["access_token"], f"{role}@example.com", role=role)
        r = client.patch(URL, headers=auth(login_token(client, f"{role}@example.com")), json={"clinic": {"name": "Hacked"}})
        assert r.status_code == 403 and r.json()["code"] == "FORBIDDEN"
    assert client.patch(URL, json={}).status_code == 401
    assert client.get(URL, headers=auth(clinic_a["access_token"])).json()["clinic"]["name"] == "Clinic A"


def test_admin_updates_profile_and_preferences_and_it_persists(client, clinic_a):
    tok = clinic_a["access_token"]
    r = client.patch(URL, headers=auth(tok), json={
        "clinic": {"name": "  Bright Smile Dental ", "address": "12 Mall Road, Lahore", "phone": "042-1234567"},
        "preferences": {"currency": "pkr", "timezone": "Asia/Karachi", "default_slot_min": 45,
                        "working_hours": {"mon": ["10:00", "18:00"], "sat": ["10:00", "14:00"]}}})
    assert r.status_code == 200
    body = client.get(URL, headers=auth(tok)).json()
    assert body["clinic"]["name"] == "Bright Smile Dental" and body["clinic"]["address"] == "12 Mall Road, Lahore"
    assert body["clinic"]["phone"] == "042-1234567"
    assert body["preferences"]["currency"] == "PKR" and body["preferences"]["default_slot_min"] == 45
    # working_hours replaces the whole schedule: days that were left out are now closed
    hours = body["preferences"]["working_hours"]
    assert hours["mon"] == ["10:00", "18:00"] and hours["sat"] == ["10:00", "14:00"]
    assert hours["tue"] is None and hours["fri"] is None and hours["sun"] is None


def test_partial_patch_leaves_everything_else_alone(client, clinic_a):
    tok = clinic_a["access_token"]
    client.patch(URL, headers=auth(tok), json={"clinic": {"address": "Somewhere", "phone": "123"}, "preferences": {"default_slot_min": 20}})
    r = client.patch(URL, headers=auth(tok), json={"preferences": {"currency": "USD"}})
    body = r.json()
    assert body["preferences"]["currency"] == "USD" and body["preferences"]["default_slot_min"] == 20
    assert body["clinic"]["address"] == "Somewhere" and body["clinic"]["phone"] == "123" and body["clinic"]["name"] == "Clinic A"
    assert client.patch(URL, headers=auth(tok), json={}).status_code == 200  # empty patch is a no-op


def test_address_and_phone_can_be_cleared_but_the_name_cannot(client, clinic_a):
    tok = clinic_a["access_token"]
    client.patch(URL, headers=auth(tok), json={"clinic": {"address": "X", "phone": "1"}})
    cleared = client.patch(URL, headers=auth(tok), json={"clinic": {"address": None, "phone": "   "}}).json()
    assert cleared["clinic"]["address"] is None and cleared["clinic"]["phone"] is None
    r = client.patch(URL, headers=auth(tok), json={"clinic": {"name": None}})
    assert r.status_code == 422 and "clinic.name" in r.json()["fields"]
    assert client.patch(URL, headers=auth(tok), json={"clinic": {"name": "A"}}).status_code == 422


@pytest.mark.parametrize("prefs, field", [
    ({"currency": "US"}, "preferences.currency"),
    ({"currency": "US1"}, "preferences.currency"),
    ({"currency": "DOLLARS"}, "preferences.currency"),
    ({"timezone": "Mars/Olympus"}, "preferences.timezone"),
    ({"timezone": ""}, "preferences.timezone"),
    ({"timezone": "../etc/passwd"}, "preferences.timezone"),
    ({"default_slot_min": 4}, "preferences.default_slot_min"),
    ({"default_slot_min": 241}, "preferences.default_slot_min"),
    ({"currency": None}, "preferences.currency"),
    ({"working_hours": {"monday": ["09:00", "17:00"]}}, "preferences.working_hours"),
    ({"working_hours": {"mon": ["9:00", "17:00"]}}, "preferences.working_hours"),
    ({"working_hours": {"mon": ["09:00", "25:00"]}}, "preferences.working_hours"),
    ({"working_hours": {"mon": ["17:00", "09:00"]}}, "preferences.working_hours"),
    ({"working_hours": {"mon": ["09:00", "09:00"]}}, "preferences.working_hours"),
    ({"working_hours": {"mon": ["09:00"]}}, "preferences.working_hours"),
    ({"working_hours": {"mon": ["09:00", "12:00", "17:00"]}}, "preferences.working_hours"),
    ({"working_hours": None}, "preferences.working_hours"),
])
def test_invalid_preferences_are_rejected_with_the_field_path(client, clinic_a, prefs, field):
    tok = clinic_a["access_token"]
    before = client.get(URL, headers=auth(tok)).json()
    r = client.patch(URL, headers=auth(tok), json={"preferences": prefs})
    assert r.status_code == 422 and r.json()["code"] == "VALIDATION_ERROR"
    assert any(k == field or k.startswith(field + ".") for k in r.json()["fields"]), r.json()
    assert client.get(URL, headers=auth(tok)).json() == before  # nothing was saved


def test_valid_unusual_values_are_accepted(client, clinic_a):
    tok = clinic_a["access_token"]
    r = client.patch(URL, headers=auth(tok), json={"preferences": {
        "timezone": "Europe/London", "default_slot_min": 5, "working_hours": {"sun": ["00:00", "23:59"]}}})
    assert r.status_code == 200 and r.json()["preferences"]["timezone"] == "Europe/London"
    assert r.json()["preferences"]["working_hours"]["sun"] == ["00:00", "23:59"]


def test_clinics_have_separate_settings_and_cannot_change_each_other(client, db, clinic_a, clinic_b):
    client.patch(URL, headers=auth(clinic_a["access_token"]), json={"clinic": {"name": "Renamed A"}, "preferences": {"currency": "USD"}})
    b = client.get(URL, headers=auth(clinic_b["access_token"])).json()
    assert b["clinic"]["name"] == "Clinic B" and b["preferences"]["currency"] == "PKR"
    # even if B's admin sends A's clinic id, only B changes
    client.patch(URL, headers=auth(clinic_b["access_token"]), json={"clinic": {"name": "Renamed B", "id": clinic_a["clinic"]["id"]}})
    assert client.get(URL, headers=auth(clinic_a["access_token"])).json()["clinic"]["name"] == "Renamed A"
    assert client.get(URL, headers=auth(clinic_b["access_token"])).json()["clinic"]["name"] == "Renamed B"
    assert db.scalar(select(func.count()).select_from(ClinicSettings)) == 2


def test_staff_in_a_clinic_see_that_clinics_settings(client, clinic_a):
    client.patch(URL, headers=auth(clinic_a["access_token"]), json={"preferences": {"default_slot_min": 15}})
    create_staff(client, clinic_a["access_token"], "doc@example.com")
    body = client.get(URL, headers=auth(login_token(client, "doc@example.com"))).json()
    assert body["preferences"]["default_slot_min"] == 15 and body["clinic"]["name"] == "Clinic A"