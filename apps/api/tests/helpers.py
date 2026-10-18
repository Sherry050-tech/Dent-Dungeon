"""Small helpers shared by the endpoint tests."""
PASSWORD = "correct-horse-battery"
TEMP_PASSWORD = "temp-password-1"


def auth(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


def register_clinic(client, email="owner@example.com", clinic="Clinic A", is_practitioner=True) -> dict:
    """Register a new clinic. Returns the response body (tokens, user, clinic)."""
    r = client.post("/api/v1/auth/register", json={
        "clinic_name": clinic, "first_name": "Owner", "last_name": "Admin",
        "email": email, "password": PASSWORD, "is_practitioner": is_practitioner})
    assert r.status_code == 201, r.text
    return r.json()


def create_staff(client, admin_token: str, email: str, role="doctor", is_practitioner=False,
                 first_name="Imran", last_name="Raza") -> dict:
    r = client.post("/api/v1/users", headers=auth(admin_token), json={
        "first_name": first_name, "last_name": last_name, "email": email,
        "temporary_password": TEMP_PASSWORD, "role": role, "is_practitioner": is_practitioner})
    assert r.status_code == 201, r.text
    return r.json()


def login_token(client, email: str, password: str = TEMP_PASSWORD) -> str:
    r = client.post("/api/v1/auth/login", json={"email": email, "password": password})
    assert r.status_code == 200, r.text
    return r.json()["access_token"]