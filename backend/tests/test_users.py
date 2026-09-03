from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from tests.conftest import auth_headers, book, create_server, create_user, login


def test_create_user(client, admin):
    headers = auth_headers(client, "admin")
    res = client.post(
        "/api/users",
        json={
            "display_name": "Neuer Nutzer",
            "email": "Neu@Example.COM",
            "password": "geheim123",
            "role": "user",
            "color": "#06b6d4",
        },
        headers=headers,
    )
    assert res.status_code == 201
    body = res.json()
    assert body["display_name"] == "Neuer Nutzer"
    assert body["email"] == "neu@example.com"
    assert body["role"] == "user"
    assert body["approved"] is True
    assert body["active"] is True
    assert body["color"] == "#06b6d4"


def test_create_user_auto_color(client, admin, db):
    create_user(db, "blau", color="#06b6d4")
    headers = auth_headers(client, "admin")
    res = client.post(
        "/api/users",
        json={"display_name": "Zwei", "email": "zwei@example.com", "password": "geheim123"},
        headers=headers,
    )
    assert res.status_code == 201
    assert res.json()["color"] == "#01adb9"


def test_color_palette_is_canonical_and_admin_only(client, admin, alice):
    expected = [
        "#01adb9",
        "#0284c7",
        "#3b82f6",
        "#4f46e5",
        "#7c3aed",
        "#9333ea",
        "#c026d3",
        "#db2777",
        "#e11d48",
        "#dc2626",
        "#ea580c",
        "#d97706",
        "#65a30d",
        "#16a34a",
        "#059669",
        "#475569",
    ]
    res = client.get("/api/users/colors", headers=auth_headers(client, "admin"))
    assert res.status_code == 200
    assert res.json() == expected
    assert len(set(res.json())) == len(expected)

    forbidden = client.get("/api/users/colors", headers=auth_headers(client, "alice"))
    assert forbidden.status_code == 403


def test_create_user_duplicate_display_name(client, admin):
    headers = auth_headers(client, "admin")
    res = client.post(
        "/api/users",
        json={"display_name": "admin", "email": "andere@example.com", "password": "geheim123"},
        headers=headers,
    )
    assert res.status_code == 409


def test_create_user_duplicate_email(client, admin):
    headers = auth_headers(client, "admin")
    res = client.post(
        "/api/users",
        json={"display_name": "Anderer", "email": "admin@example.local", "password": "geheim123"},
        headers=headers,
    )
    assert res.status_code == 409


def test_create_user_integrity_race_returns_409(client, admin, monkeypatch):
    headers = auth_headers(client, "admin")

    def fail_commit(_: Session) -> None:
        raise IntegrityError("INSERT", {}, Exception("unique race"))

    monkeypatch.setattr(Session, "commit", fail_commit)
    res = client.post(
        "/api/users",
        json={"display_name": "Race", "email": "race@example.com", "password": "geheim123"},
        headers=headers,
    )
    assert res.status_code == 409


def test_create_user_short_password(client, admin):
    headers = auth_headers(client, "admin")
    res = client.post(
        "/api/users",
        json={"display_name": "Kurz", "email": "kurz@example.com", "password": "x"},
        headers=headers,
    )
    assert res.status_code == 422


def test_create_user_forbidden_for_user(client, alice):
    headers = auth_headers(client, "alice")
    res = client.post(
        "/api/users",
        json={"display_name": "Neuer", "email": "neu@example.com", "password": "geheim123"},
        headers=headers,
    )
    assert res.status_code == 403


def test_list_users_requires_admin(client, admin, alice):
    res = client.get("/api/users", headers=auth_headers(client, "alice"))
    assert res.status_code == 403

    res = client.get("/api/users", headers=auth_headers(client, "admin"))
    assert res.status_code == 200
    display_names = {u["display_name"] for u in res.json()}
    assert display_names == {"admin", "alice"}


def test_admin_can_approve_registration(client, admin):
    registered = client.post(
        "/api/auth/register",
        json={
            "display_name": "Pending",
            "email": "pending@example.com",
            "password": "Sicher123",
            "password_confirmation": "Sicher123",
        },
    )
    assert registered.status_code == 201

    users = client.get("/api/users", headers=auth_headers(client, "admin")).json()
    pending = next(user for user in users if user["email"] == "pending@example.com")
    directory = client.get("/api/users/directory", headers=auth_headers(client, "admin")).json()
    assert all(user["id"] != pending["id"] for user in directory)
    approved = client.patch(
        f"/api/users/{pending['id']}",
        json={"approved": True},
        headers=auth_headers(client, "admin"),
    )
    assert approved.status_code == 200
    assert approved.json()["approved"] is True
    assert login(client, "pending@example.com", "Sicher123")


def test_user_directory_does_not_expose_emails(client, admin, alice):
    res = client.get("/api/users/directory", headers=auth_headers(client, "alice"))
    assert res.status_code == 200
    assert {user["display_name"] for user in res.json()} == {"admin", "alice"}
    assert all(set(user) == {"id", "display_name", "color"} for user in res.json())


def test_update_role_and_color(client, admin, alice):
    headers = auth_headers(client, "admin")
    res = client.patch("/api/users/2", json={"role": "admin", "color": "#ef4444"}, headers=headers)
    assert res.status_code == 200
    body = res.json()
    assert body["role"] == "admin"
    assert body["color"] == "#ef4444"


def test_last_admin_cannot_be_demoted(client, admin):
    res = client.patch(
        f"/api/users/{admin.id}",
        json={"role": "user"},
        headers=auth_headers(client, "admin"),
    )
    assert res.status_code == 409
    assert "letzte Administrator" in res.json()["detail"]


def test_last_admin_cannot_be_unapproved(client, admin):
    res = client.patch(
        f"/api/users/{admin.id}",
        json={"approved": False},
        headers=auth_headers(client, "admin"),
    )
    assert res.status_code == 409
    assert "letzte Administrator" in res.json()["detail"]


def test_last_admin_cannot_be_deactivated_or_deleted(client, admin):
    headers = auth_headers(client, "admin")
    deactivated = client.patch(f"/api/users/{admin.id}", json={"active": False}, headers=headers)
    assert deactivated.status_code == 409
    assert "letzte Administrator" in deactivated.json()["detail"]

    deleted = client.delete(f"/api/users/{admin.id}", headers=headers)
    assert deleted.status_code == 409
    assert "letzte Administrator" in deleted.json()["detail"]


def test_admin_can_delete_unused_user_and_memberships(client, admin, bob):
    headers = auth_headers(client, "admin")
    project = client.post(
        "/api/projects",
        json={"name": "Mitgliedschaft", "member_ids": [bob.id]},
        headers=headers,
    )
    assert project.status_code == 201

    deleted = client.delete(f"/api/users/{bob.id}", headers=headers)
    assert deleted.status_code == 204
    assert all(user["id"] != bob.id for user in client.get("/api/users", headers=headers).json())


def test_delete_user_deletes_own_bookings_and_transfers_projects(client, admin, alice, bob):
    admin_token = login(client, "admin")
    server = create_server(client, "delete-user-server", admin_token)
    alice_token = login(client, "alice")
    created = client.post(
        "/api/projects",
        json={"name": "Alice-Projekt"},
        headers={"Authorization": f"Bearer {alice_token}"},
    )
    assert created.status_code == 201
    project_id = created.json()["id"]
    alice_booking = book(
        client,
        alice_token,
        gpu_ids=[],
        mode="cpu",
        project_id=project_id,
        server_id=server["id"],
        start="2026-06-01T08:00:00",
        end="2026-06-01T10:00:00",
    )
    bob_booking = book(
        client,
        login(client, "bob"),
        gpu_ids=[],
        mode="cpu",
        project_id=project_id,
        server_id=server["id"],
        start="2026-06-01T10:00:00",
        end="2026-06-01T12:00:00",
    )
    assert alice_booking.status_code == bob_booking.status_code == 201

    headers = auth_headers(client, "admin")
    deleted = client.delete(f"/api/users/{alice.id}", headers=headers)
    assert deleted.status_code == 204

    projects = client.get("/api/projects", headers=headers).json()
    project = next(project for project in projects if project["id"] == project_id)
    assert project["owner_id"] == admin.id
    bookings = client.get(
        "/api/bookings?from=2026-06-01T00:00:00&to=2026-06-02T00:00:00",
        headers=headers,
    ).json()
    assert [booking["id"] for booking in bookings] == [bob_booking.json()["id"]]


def test_admin_can_be_demoted_when_another_admin_exists(client, admin, alice):
    headers = auth_headers(client, "admin")
    promoted = client.patch(f"/api/users/{alice.id}", json={"role": "admin"}, headers=headers)
    assert promoted.status_code == 200

    demoted = client.patch(f"/api/users/{admin.id}", json={"role": "user"}, headers=headers)
    assert demoted.status_code == 200
    assert demoted.json()["role"] == "user"


def test_update_user_rejects_explicit_null(client, admin, alice):
    headers = auth_headers(client, "admin")
    for field in ("display_name", "email", "role", "color", "password", "approved", "active"):
        res = client.patch(f"/api/users/{alice.id}", json={field: None}, headers=headers)
        assert res.status_code == 422


def test_update_display_name_and_email(client, admin, alice):
    headers = auth_headers(client, "admin")
    res = client.patch(
        "/api/users/2",
        json={"display_name": "Alice Example", "email": "ALICE.NEU@EXAMPLE.COM"},
        headers=headers,
    )
    assert res.status_code == 200
    assert res.json()["display_name"] == "Alice Example"
    assert res.json()["email"] == "alice.neu@example.com"
    assert login(client, "alice.neu@example.com")


def test_update_legacy_mixed_case_email_does_not_conflict(client, admin, alice, db):
    alice.email = "Alice@Example.Local"
    db.commit()

    res = client.patch(
        f"/api/users/{alice.id}",
        json={"email": "alice@example.local", "color": "#01adb9"},
        headers=auth_headers(client, "admin"),
    )
    assert res.status_code == 200
    assert res.json()["email"] == "alice@example.local"


def test_reset_password(client, admin, alice):
    headers = auth_headers(client, "admin")
    res = client.patch("/api/users/2", json={"password": "neuespasswort"}, headers=headers)
    assert res.status_code == 200
    login_res = client.post(
        "/api/auth/login", json={"email": "alice@example.local", "password": "neuespasswort"}
    )
    assert login_res.status_code == 200


def test_update_user_not_found(client, admin):
    res = client.patch("/api/users/999", json={"role": "admin"}, headers=auth_headers(client, "admin"))
    assert res.status_code == 404
