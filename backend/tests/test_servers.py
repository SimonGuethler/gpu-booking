from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from tests.conftest import (
    auth_headers,
    book,
    create_gpu,
    create_project,
    create_server,
    login,
)


def test_create_and_list_servers(client, admin):
    token = login(client, "admin")
    create_server(client, "gpu-cluster", token)
    create_server(client, "testbox", token)

    res = client.get("/api/servers", headers=auth_headers(client, "admin"))
    assert res.status_code == 200
    names = {s["name"] for s in res.json()}
    assert names == {"gpu-cluster", "testbox"}


def test_create_server_duplicate(client, admin):
    token = login(client, "admin")
    create_server(client, "gpu-cluster", token)
    res = client.post("/api/servers", json={"name": "gpu-cluster"}, headers=auth_headers(client, "admin"))
    assert res.status_code == 409


def test_create_server_integrity_race_returns_409(client, admin, monkeypatch):
    headers = auth_headers(client, "admin")

    def fail_commit(_: Session) -> None:
        raise IntegrityError("INSERT", {}, Exception("unique race"))

    monkeypatch.setattr(Session, "commit", fail_commit)
    res = client.post("/api/servers", json={"name": "race"}, headers=headers)
    assert res.status_code == 409


def test_create_server_forbidden_for_user(client, alice):
    res = client.post("/api/servers", json={"name": "cluster"}, headers=auth_headers(client, "alice"))
    assert res.status_code == 403


def test_update_server(client, admin):
    token = login(client, "admin")
    server = create_server(client, "gpu-cluster", token)
    res = client.patch(
        f"/api/servers/{server['id']}",
        json={"active": False},
        headers=auth_headers(client, "admin"),
    )
    assert res.status_code == 200
    assert res.json()["active"] is False


def test_update_server_nullable_and_required_patch_fields(client, admin):
    token = login(client, "admin")
    headers = {"Authorization": f"Bearer {token}"}
    server = create_server(client, "gpu-cluster", token)

    unchanged = client.patch(f"/api/servers/{server['id']}", json={}, headers=headers)
    assert unchanged.status_code == 200
    assert unchanged.json()["hostname"] == "gpu-cluster.local"

    cleared = client.patch(f"/api/servers/{server['id']}", json={"hostname": None}, headers=headers)
    assert cleared.status_code == 200
    assert cleared.json()["hostname"] is None

    for field in ("name", "active"):
        invalid = client.patch(f"/api/servers/{server['id']}", json={field: None}, headers=headers)
        assert invalid.status_code == 422


def test_delete_server_without_gpus(client, admin):
    token = login(client, "admin")
    server = create_server(client, "leer", token)
    res = client.delete(f"/api/servers/{server['id']}", headers=auth_headers(client, "admin"))
    assert res.status_code == 204
    assert client.get("/api/servers", headers=auth_headers(client, "admin")).json() == []


def test_delete_server_deactivates_booked_gpus(client, admin, alice, bob):
    token = login(client, "admin")
    server = create_server(client, "cluster", token)
    gpu = create_gpu(client, server["id"], "A6000 #0", token)
    project = create_project(client, "P", token)
    alice_token = login(client, "alice")

    res = book(
        client,
        alice_token,
        gpu_ids=[gpu["id"]],
        mode="dev",
        project_id=project["id"],
        start="2026-06-01T10:00:00",
        end="2026-06-01T12:00:00",
    )
    assert res.status_code == 201

    res = client.delete(f"/api/servers/{server['id']}", headers=auth_headers(client, "admin"))
    assert res.status_code == 204

    servers = client.get("/api/servers", headers=auth_headers(client, "bob")).json()
    assert servers[0]["active"] is False
    assert servers[0]["gpus"][0]["active"] is False


def test_create_gpu(client, admin):
    token = login(client, "admin")
    server = create_server(client, "cluster", token)
    gpu = create_gpu(client, server["id"], "A6000 #0", token)
    assert gpu["memory_mb"] == 49152
    assert gpu["server_id"] == server["id"]


def test_update_gpu(client, admin):
    token = login(client, "admin")
    server = create_server(client, "cluster", token)
    gpu = create_gpu(client, server["id"], "A6000 #0", token)
    res = client.patch(
        f"/api/gpus/{gpu['id']}", json={"active": False}, headers=auth_headers(client, "admin")
    )
    assert res.status_code == 200
    assert res.json()["active"] is False


def test_update_gpu_nullable_and_required_patch_fields(client, admin):
    token = login(client, "admin")
    headers = {"Authorization": f"Bearer {token}"}
    server = create_server(client, "cluster", token)
    gpu = create_gpu(client, server["id"], "A6000 #0", token)

    unchanged = client.patch(f"/api/gpus/{gpu['id']}", json={}, headers=headers)
    assert unchanged.status_code == 200
    assert unchanged.json()["memory_mb"] == 49152

    cleared = client.patch(f"/api/gpus/{gpu['id']}", json={"memory_mb": None}, headers=headers)
    assert cleared.status_code == 200
    assert cleared.json()["memory_mb"] is None

    for field in ("name", "active"):
        invalid = client.patch(f"/api/gpus/{gpu['id']}", json={field: None}, headers=headers)
        assert invalid.status_code == 422


def test_delete_gpu_with_bookings_conflict(client, admin, alice):
    token = login(client, "admin")
    server = create_server(client, "cluster", token)
    gpu = create_gpu(client, server["id"], "A6000 #0", token)
    project = create_project(client, "P", token)

    res = book(
        client,
        login(client, "alice"),
        gpu_ids=[gpu["id"]],
        mode="train",
        project_id=project["id"],
        start="2026-06-01T10:00:00",
        end="2026-06-01T12:00:00",
    )
    assert res.status_code == 201

    res = client.delete(f"/api/gpus/{gpu['id']}", headers=auth_headers(client, "admin"))
    assert res.status_code == 409

    res = client.delete(f"/api/gpus/{gpu['id']}", headers=auth_headers(client, "admin"))
    assert res.status_code == 409


def test_delete_free_gpu(client, admin):
    token = login(client, "admin")
    server = create_server(client, "cluster", token)
    gpu = create_gpu(client, server["id"], "A6000 #0", token)
    res = client.delete(f"/api/gpus/{gpu['id']}", headers=auth_headers(client, "admin"))
    assert res.status_code == 204


def test_gpu_delete_forbidden_for_user(client, admin, alice):
    token = login(client, "admin")
    server = create_server(client, "cluster", token)
    gpu = create_gpu(client, server["id"], "A6000 #0", token)
    res = client.delete(f"/api/gpus/{gpu['id']}", headers=auth_headers(client, "alice"))
    assert res.status_code == 403
