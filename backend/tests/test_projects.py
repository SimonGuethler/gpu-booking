from tests.conftest import auth_headers, book, login


def test_create_project_owner_and_member(client, admin, alice, bob):
    token = login(client, "alice")
    res = client.post(
        "/api/projects",
        json={"name": "LLM-Feintuning", "description": "LoRA", "member_ids": [1, 3]},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert res.status_code == 201
    body = res.json()
    assert body["owner_id"] == 2
    member_ids = {m["id"] for m in body["members"]}
    assert member_ids == {2, 1, 3}


def test_create_project_duplicate(client, admin):

    res = client.post("/api/projects", json={"name": "Projekt"}, headers=auth_headers(client, "admin"))
    assert res.status_code == 201
    res = client.post("/api/projects", json={"name": "Projekt"}, headers=auth_headers(client, "admin"))
    assert res.status_code == 409


def test_projects_visible_to_all(client, admin, alice):

    client.post("/api/projects", json={"name": "Projekt A"}, headers=auth_headers(client, "admin"))
    res = client.get("/api/projects", headers=auth_headers(client, "alice"))
    assert res.status_code == 200
    assert len(res.json()) == 1


def test_owner_can_edit(client, admin, alice, bob):
    token = login(client, "alice")
    project_id = create_project_id(client, "Projekt", token)
    res = client.patch(
        f"/api/projects/{project_id}",
        json={"name": "Projekt neu", "member_ids": [1]},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert res.status_code == 200
    assert res.json()["name"] == "Projekt neu"
    assert {m["id"] for m in res.json()["members"]} == {2, 1}


def test_admin_can_edit_foreign_project(client, admin, alice):
    token = login(client, "alice")
    project_id = create_project_id(client, "Projekt", token)
    res = client.patch(
        f"/api/projects/{project_id}",
        json={"active": False},
        headers=auth_headers(client, "admin"),
    )
    assert res.status_code == 200
    assert res.json()["active"] is False


def test_update_project_nullable_and_required_patch_fields(client, admin):
    token = login(client, "admin")
    headers = {"Authorization": f"Bearer {token}"}
    project_id = create_project_id(client, "Projekt", token)

    unchanged = client.patch(f"/api/projects/{project_id}", json={}, headers=headers)
    assert unchanged.status_code == 200
    assert unchanged.json()["description"] is None

    client.patch(
        f"/api/projects/{project_id}",
        json={"description": "Dokumentation"},
        headers=headers,
    )
    cleared = client.patch(f"/api/projects/{project_id}", json={"description": None}, headers=headers)
    assert cleared.status_code == 200
    assert cleared.json()["description"] is None

    for field in ("name", "active", "member_ids"):
        invalid = client.patch(f"/api/projects/{project_id}", json={field: None}, headers=headers)
        assert invalid.status_code == 422


def test_other_user_cannot_edit(client, admin, alice, bob):
    token = login(client, "alice")
    project_id = create_project_id(client, "Projekt", token)
    res = client.patch(
        f"/api/projects/{project_id}",
        json={"name": "fremd"},
        headers=auth_headers(client, "bob"),
    )
    assert res.status_code == 403


def test_inactive_project_hidden_from_users(client, admin, alice):
    token = login(client, "alice")
    project_id = create_project_id(client, "Projekt", token)
    client.patch(
        f"/api/projects/{project_id}",
        json={"active": False},
        headers=auth_headers(client, "admin"),
    )
    res = client.get("/api/projects", headers=auth_headers(client, "alice"))
    assert res.json() == []
    res = client.get("/api/projects", headers=auth_headers(client, "admin"))
    assert len(res.json()) == 1


def test_delete_project_owner(client, admin, alice):
    token = login(client, "alice")
    project_id = create_project_id(client, "Projekt", token)
    res = client.delete(f"/api/projects/{project_id}", headers={"Authorization": f"Bearer {token}"})
    assert res.status_code == 204


def test_delete_project_deletes_its_bookings(client, admin, alice):
    token = login(client, "alice")
    server_id = create_server_and_gpu(client, admin)
    project_id = create_project_id(client, "Projekt", token)
    res = book(
        client,
        token,
        gpu_ids=[],
        mode="cpu",
        project_id=project_id,
        server_id=server_id,
        start="2026-06-01T10:00:00",
        end="2026-06-01T12:00:00",
    )
    assert res.status_code == 201
    res = client.delete(f"/api/projects/{project_id}", headers={"Authorization": f"Bearer {token}"})
    assert res.status_code == 204
    bookings = client.get(
        "/api/bookings?from=2026-06-01T00:00:00&to=2026-06-02T00:00:00",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert bookings.status_code == 200
    assert bookings.json() == []


def test_delete_project_forbidden_for_member(client, admin, alice, bob):
    alice_token = login(client, "alice")
    project_id = create_project_id(client, "Projekt", alice_token)
    client.patch(
        f"/api/projects/{project_id}",
        json={"member_ids": [3]},
        headers={"Authorization": f"Bearer {alice_token}"},
    )
    res = client.delete(f"/api/projects/{project_id}", headers=auth_headers(client, "bob"))
    assert res.status_code == 403


def create_project_id(client, name: str, token: str) -> int:
    res = client.post("/api/projects", json={"name": name}, headers={"Authorization": f"Bearer {token}"})
    assert res.status_code == 201
    return res.json()["id"]


def create_server_and_gpu(client, admin) -> int:
    res = client.post("/api/servers", json={"name": "cluster"}, headers=auth_headers(client, "admin"))
    server_id = res.json()["id"]
    res = client.post(
        f"/api/servers/{server_id}/gpus", json={"name": "A6000 #0"}, headers=auth_headers(client, "admin")
    )
    assert res.status_code == 201
    return server_id
