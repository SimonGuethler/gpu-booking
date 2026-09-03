from app.security import AUTH_COOKIE_NAME, CSRF_COOKIE_NAME, DUMMY_PASSWORD_HASH
from tests.conftest import PASSWORD, auth_headers


def test_login_ok(client, admin):
    res = client.post("/api/auth/login", json={"email": "admin@example.local", "password": PASSWORD})
    assert res.status_code == 200
    body = res.json()
    assert body["token_type"] == "bearer"
    assert body["user"]["display_name"] == "admin"
    assert body["user"]["role"] == "admin"
    assert body["access_token"]
    assert res.cookies.get(AUTH_COOKIE_NAME)
    assert res.cookies.get(CSRF_COOKIE_NAME) == res.headers["X-CSRF-Token"]
    session_cookie = next(
        cookie for cookie in res.headers.get_list("set-cookie") if cookie.startswith(AUTH_COOKIE_NAME)
    )
    assert "HttpOnly" in session_cookie
    assert "SameSite=strict" in session_cookie
    assert res.headers["cache-control"] == "no-store"


def test_login_wrong_password(client, admin):
    res = client.post("/api/auth/login", json={"email": "admin@example.local", "password": "falsch123"})
    assert res.status_code == 401


def test_registration_requires_approval(client, db):
    res = client.post(
        "/api/auth/register",
        json={
            "display_name": "Neue Person",
            "email": "NEU@example.com",
            "password": "Sicher123",
            "password_confirmation": "Sicher123",
        },
    )
    assert res.status_code == 201
    assert "Freigabe" in res.json()["message"]

    db.expire_all()
    from app.models import User

    user = db.query(User).filter_by(email="neu@example.com").one()
    assert user.approved is False
    assert user.active is True
    assert user.role == "user"

    login_res = client.post(
        "/api/auth/login",
        json={"email": "neu@example.com", "password": "Sicher123"},
    )
    assert login_res.status_code == 403
    assert "Freigabe" in login_res.json()["detail"]


def test_registration_validates_password_and_confirmation(client):
    base = {
        "display_name": "Neue Person",
        "email": "neu@example.com",
        "password_confirmation": "Sicher123",
    }
    for password in ("kurz1A", "klein123", "GROSS123", "OhneZahl"):
        res = client.post("/api/auth/register", json={**base, "password": password})
        assert res.status_code == 422

    mismatch = client.post(
        "/api/auth/register",
        json={**base, "password": "Sicher123", "password_confirmation": "Anders123"},
    )
    assert mismatch.status_code == 422


def test_login_unknown_user_runs_password_verification(client, monkeypatch):
    calls: list[tuple[str, str]] = []

    def track_verification(password: str, stored: str) -> bool:
        calls.append((password, stored))
        return False

    monkeypatch.setattr("app.routers.auth.verify_password", track_verification)
    res = client.post("/api/auth/login", json={"email": "gibtsnicht@example.local", "password": PASSWORD})
    assert res.status_code == 401
    assert calls == [(PASSWORD, DUMMY_PASSWORD_HASH)]


def test_login_rejects_overlong_password_before_hashing(client, monkeypatch):
    def unexpected_verification(_: str, __: str) -> bool:
        raise AssertionError("Überlange Passwörter dürfen nicht gehasht werden.")

    monkeypatch.setattr("app.routers.auth.verify_password", unexpected_verification)
    res = client.post(
        "/api/auth/login",
        json={"email": "gibtsnicht@example.local", "password": "x" * 201},
    )
    assert res.status_code == 422


def test_me(client, admin):
    headers = auth_headers(client, "admin")
    res = client.get("/api/auth/me", headers=headers)
    assert res.status_code == 200
    assert res.json()["display_name"] == "admin"


def test_me_missing_token(client):
    res = client.get("/api/auth/me")
    assert res.status_code == 401


def test_me_invalid_token(client):
    res = client.get("/api/auth/me", headers={"Authorization": "Bearer kaputt"})
    assert res.status_code == 401


def test_deactivated_user_cannot_login_or_use_existing_session(client, admin, alice):
    alice_headers = auth_headers(client, "alice")
    disabled = client.patch(
        f"/api/users/{alice.id}",
        json={"active": False},
        headers=auth_headers(client, "admin"),
    )
    assert disabled.status_code == 200
    assert disabled.json()["active"] is False

    login_res = client.post(
        "/api/auth/login",
        json={"email": "alice@example.local", "password": PASSWORD},
    )
    assert login_res.status_code == 403
    assert "deaktiviert" in login_res.json()["detail"]
    assert client.get("/api/auth/me", headers=alice_headers).status_code == 401


def test_login_normalizes_email(client, admin):
    res = client.post(
        "/api/auth/login",
        json={"email": "  ADMIN@EXAMPLE.LOCAL  ", "password": PASSWORD},
    )
    assert res.status_code == 200


def test_cookie_session_requires_csrf_for_mutations_and_can_logout(client, admin):
    login_res = client.post(
        "/api/auth/login",
        json={"email": "admin@example.local", "password": PASSWORD},
    )
    csrf_token = login_res.headers["X-CSRF-Token"]

    me = client.get("/api/auth/me")
    assert me.status_code == 200
    assert me.json()["id"] == admin.id

    blocked = client.post("/api/projects", json={"name": "Ohne CSRF"})
    assert blocked.status_code == 403

    allowed = client.post(
        "/api/projects",
        json={"name": "Mit CSRF"},
        headers={"X-CSRF-Token": csrf_token},
    )
    assert allowed.status_code == 201

    logout = client.post("/api/auth/logout", headers={"X-CSRF-Token": csrf_token})
    assert logout.status_code == 204
    assert client.get("/api/auth/me").status_code == 401
