import hashlib
import os

from app.config import get_settings
from app.models import User
from app.security import (
    AUTH_COOKIE_NAME,
    CSRF_COOKIE_NAME,
    DUMMY_PASSWORD_HASH,
    LEGACY_PBKDF2_ITERATIONS,
    PASSWORD_ALGORITHM,
    create_access_token,
    verify_password,
)
from tests.conftest import PASSWORD, auth_headers, login


def test_login_ok(client, admin):
    res = client.post("/api/auth/login", json={"email": "admin@example.local", "password": PASSWORD})
    assert res.status_code == 200
    body = res.json()
    assert set(body) == {"user"}
    assert body["user"]["display_name"] == "admin"
    assert body["user"]["role"] == "admin"
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


def test_registration_rejects_case_insensitive_duplicate_name(client):
    body = {
        "display_name": "Neue Person",
        "email": "neu@example.com",
        "password": "Sicher123",
        "password_confirmation": "Sicher123",
    }
    assert client.post("/api/auth/register", json=body).status_code == 201

    dupe = dict(body, display_name="NEUE PERSON", email="anders@example.com")
    assert client.post("/api/auth/register", json=dupe).status_code == 409


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


def _legacy_hash(password: str) -> str:
    salt = os.urandom(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, LEGACY_PBKDF2_ITERATIONS)
    return f"{salt.hex()}${digest.hex()}"


def _reload_user(db, email: str) -> User:
    db.expire_all()
    return db.query(User).filter_by(email=email).one()


def test_login_upgrades_legacy_password_hash(client, admin, db):
    admin.password_hash = _legacy_hash(PASSWORD)
    db.commit()

    res = client.post("/api/auth/login", json={"email": "admin@example.local", "password": PASSWORD})
    assert res.status_code == 200

    user = _reload_user(db, "admin@example.local")
    algorithm, iterations, _salt, _digest = user.password_hash.split("$")
    assert algorithm == PASSWORD_ALGORITHM
    assert int(iterations) == get_settings().pbkdf2_iterations
    assert verify_password(PASSWORD, user.password_hash)


def test_login_upgrades_hash_with_outdated_iterations(client, admin, db):
    salt = os.urandom(16)
    digest = hashlib.pbkdf2_hmac("sha256", PASSWORD.encode("utf-8"), salt, 123)
    stale = f"{PASSWORD_ALGORITHM}$123${salt.hex()}${digest.hex()}"
    admin.password_hash = stale
    db.commit()

    assert verify_password(PASSWORD, stale)
    res = client.post("/api/auth/login", json={"email": "admin@example.local", "password": PASSWORD})
    assert res.status_code == 200

    user = _reload_user(db, "admin@example.local")
    assert user.password_hash != stale
    assert int(user.password_hash.split("$")[1]) == get_settings().pbkdf2_iterations


def test_login_keeps_current_password_hash(client, admin, db):
    stored_before = admin.password_hash

    res = client.post("/api/auth/login", json={"email": "admin@example.local", "password": PASSWORD})
    assert res.status_code == 200

    user = _reload_user(db, "admin@example.local")
    assert user.password_hash == stored_before


def test_login_wrong_password_does_not_rehash(client, admin, db):
    stored_before = admin.password_hash

    res = client.post("/api/auth/login", json={"email": "admin@example.local", "password": "falsch123"})
    assert res.status_code == 401

    user = _reload_user(db, "admin@example.local")
    assert user.password_hash == stored_before


def test_login_rehash_does_not_invalidate_other_sessions(client, admin, db):
    admin.password_hash = _legacy_hash(PASSWORD)
    db.commit()

    token_device_a = login(client, "admin")
    token_device_b = login(client, "admin")

    user = _reload_user(db, "admin@example.local")
    assert user.password_hash.startswith(PASSWORD_ALGORITHM)
    res_a = client.get("/api/auth/me", headers={"Authorization": f"Bearer {token_device_a}"})
    res_b = client.get("/api/auth/me", headers={"Authorization": f"Bearer {token_device_b}"})
    assert res_a.status_code == 200
    assert res_b.status_code == 200


def test_token_without_pwd_claim_survives_upgrade_until_password_change(client, admin):
    # Tokens ausgestellt vor dem Upgrade besitzen keinen pwd-Claim.
    legacy_token = create_access_token(admin.id, None)
    headers = {"Authorization": f"Bearer {legacy_token}"}
    assert client.get("/api/auth/me", headers=headers).status_code == 200

    change_res = client.patch(
        f"/api/users/{admin.id}",
        json={"password": "neuespasswort"},
        headers=auth_headers(client, "admin", PASSWORD),
    )
    assert change_res.status_code == 200

    res = client.get("/api/auth/me", headers=headers)
    assert res.status_code == 401
    assert "Passwortänderung" in res.json()["detail"]


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
