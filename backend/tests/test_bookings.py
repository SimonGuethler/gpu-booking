from types import SimpleNamespace

from tests.conftest import auth_headers, book, create_gpu, create_project, create_server, login


def setup_resource(client, admin_token: str) -> tuple[int, int]:
    server = create_server(client, "cluster", admin_token)
    gpu = create_gpu(client, server["id"], "A6000 #0", admin_token)
    project = create_project(client, "Projekt", admin_token)
    return gpu["id"], project["id"]


def test_create_train_booking(client, admin, alice):
    admin_token = login(client, "admin")
    gpu_id, project_id = setup_resource(client, admin_token)
    res = book(
        client,
        login(client, "alice"),
        gpu_ids=[gpu_id],
        mode="train",
        project_id=project_id,
        start="2026-06-01T14:00:00",
        end="2026-06-01T16:00:00",
    )
    assert res.status_code == 201
    body = res.json()
    assert body["mode"] == "train"
    assert body["user"]["display_name"] == "alice"
    assert body["gpus"][0]["id"] == gpu_id
    assert body["project"]["name"] == "Projekt"


def test_gpu_booking_must_stay_on_one_server(client, admin, alice):
    admin_token = login(client, "admin")
    first_server = create_server(client, "cluster-a", admin_token)
    second_server = create_server(client, "cluster-b", admin_token)
    first_gpu = create_gpu(client, first_server["id"], "A6000 #0", admin_token)
    second_gpu = create_gpu(client, second_server["id"], "A6000 #1", admin_token)
    project = create_project(client, "Serverbindung", admin_token)

    res = book(
        client,
        login(client, "alice"),
        gpu_ids=[first_gpu["id"], second_gpu["id"]],
        mode="train",
        project_id=project["id"],
        start="2026-06-01T14:00:00",
        end="2026-06-01T16:00:00",
    )

    assert res.status_code == 400
    assert "selben Server" in res.json()["detail"]


def test_missing_project_422(client, admin, alice):
    admin_token = login(client, "admin")
    gpu_id, _ = setup_resource(client, admin_token)
    res = client.post(
        "/api/bookings",
        json={
            "gpu_ids": [gpu_id],
            "mode": "train",
            "start_at": "2026-06-01T14:00:00",
            "end_at": "2026-06-01T16:00:00",
        },
        headers=auth_headers(client, "alice"),
    )
    assert res.status_code == 422


def test_train_requires_gpu(client, admin, alice):
    _, project_id = setup_resource(client, login(client, "admin"))
    res = book(
        client,
        login(client, "alice"),
        gpu_ids=[],
        mode="train",
        project_id=project_id,
        start="2026-06-01T14:00:00",
        end="2026-06-01T16:00:00",
    )
    assert res.status_code == 422


def test_cpu_forbids_gpus(client, admin, alice):
    admin_token = login(client, "admin")
    gpu_id, project_id = setup_resource(client, admin_token)
    res = book(
        client,
        login(client, "alice"),
        gpu_ids=[gpu_id],
        mode="cpu",
        project_id=project_id,
        start="2026-06-01T14:00:00",
        end="2026-06-01T16:00:00",
    )
    assert res.status_code == 422


def test_cpu_requires_and_returns_server(client, admin, alice):
    admin_token = login(client, "admin")
    server = create_server(client, "cpu-cluster", admin_token)
    project = create_project(client, "CPU-Projekt", admin_token)
    alice_token = login(client, "alice")

    missing_server = book(
        client,
        alice_token,
        gpu_ids=[],
        mode="cpu",
        project_id=project["id"],
        start="2026-06-01T14:00:00",
        end="2026-06-01T16:00:00",
    )
    assert missing_server.status_code == 422

    res = book(
        client,
        alice_token,
        gpu_ids=[],
        mode="cpu",
        project_id=project["id"],
        server_id=server["id"],
        start="2026-06-01T14:00:00",
        end="2026-06-01T16:00:00",
    )
    assert res.status_code == 201
    assert res.json()["server_id"] == server["id"]

    filtered = client.get(
        f"/api/bookings?from=2026-06-01T00:00:00&to=2026-06-02T00:00:00&server_id={server['id']}",
        headers={"Authorization": f"Bearer {alice_token}"},
    )
    assert filtered.status_code == 200
    assert [booking["id"] for booking in filtered.json()] == [res.json()["id"]]


def test_hour_grid_enforced(client, admin, alice):
    admin_token = login(client, "admin")
    gpu_id, project_id = setup_resource(client, admin_token)
    res = book(
        client,
        login(client, "alice"),
        gpu_ids=[gpu_id],
        mode="train",
        project_id=project_id,
        start="2026-06-01T14:30:00",
        end="2026-06-01T16:00:00",
    )
    assert res.status_code == 422
    res = book(
        client,
        login(client, "alice"),
        gpu_ids=[gpu_id],
        mode="train",
        project_id=project_id,
        start="2026-06-01T16:00:00",
        end="2026-06-01T16:00:00",
    )
    assert res.status_code == 422


def test_adjacent_bookings_ok(client, admin, alice, bob):
    admin_token = login(client, "admin")
    gpu_id, project_id = setup_resource(client, admin_token)
    t = login(client, "alice")
    res = book(
        client,
        t,
        gpu_ids=[gpu_id],
        mode="train",
        project_id=project_id,
        start="2026-06-01T14:00:00",
        end="2026-06-01T15:00:00",
    )
    assert res.status_code == 201
    res = book(
        client,
        login(client, "bob"),
        gpu_ids=[gpu_id],
        mode="train",
        project_id=project_id,
        start="2026-06-01T15:00:00",
        end="2026-06-01T16:00:00",
    )
    assert res.status_code == 201


def test_conflict_matrix(client, admin, alice, bob):
    admin_token = login(client, "admin")
    gpu_id, project_id = setup_resource(client, admin_token)
    alice_t = login(client, "alice")
    bob_t = login(client, "bob")

    cases = [("train", "train", 409), ("train", "dev", 409), ("dev", "train", 409), ("dev", "dev", 201)]
    days = ["2026-06-02", "2026-06-03", "2026-06-04", "2026-06-05"]
    for (first_mode, second_mode, expected), day in zip(cases, days, strict=True):
        setup = book(
            client,
            alice_t,
            gpu_ids=[gpu_id],
            mode=first_mode,
            project_id=project_id,
            start=f"{day}T10:00:00",
            end=f"{day}T12:00:00",
        )
        assert setup.status_code == 201, (first_mode, setup.text)
        res = book(
            client,
            bob_t,
            gpu_ids=[gpu_id],
            mode=second_mode,
            project_id=project_id,
            start=f"{day}T11:00:00",
            end=f"{day}T13:00:00",
        )
        assert res.status_code == expected, (first_mode, second_mode, res.text)
        if expected == 201:
            assert "Konflikt" not in res.text
        else:
            detail = res.json()["detail"]
            assert detail["code"] == "booking_conflict"
            assert "Konflikt" in detail["message"]
            assert detail["start_at"] == f"{day}T10:00:00"
            assert detail["end_at"] == f"{day}T12:00:00"


def test_conflict_selection_is_deterministic(client, admin, alice, bob):
    admin_token = login(client, "admin")
    gpu_id, project_id = setup_resource(client, admin_token)

    later = book(
        client,
        login(client, "alice"),
        gpu_ids=[gpu_id],
        mode="dev",
        project_id=project_id,
        start="2026-06-08T11:00:00",
        end="2026-06-08T14:00:00",
    )
    assert later.status_code == 201
    earlier = book(
        client,
        login(client, "bob"),
        gpu_ids=[gpu_id],
        mode="dev",
        project_id=project_id,
        start="2026-06-08T10:00:00",
        end="2026-06-08T13:00:00",
    )
    assert earlier.status_code == 201

    conflict = book(
        client,
        admin_token,
        gpu_ids=[gpu_id],
        mode="train",
        project_id=project_id,
        start="2026-06-08T12:00:00",
        end="2026-06-08T13:00:00",
    )
    assert conflict.status_code == 409
    detail = conflict.json()["detail"]
    assert detail["start_at"] == "2026-06-08T10:00:00"
    assert "bob (Teilbelegung)" in detail["message"]


def test_cpu_never_conflicts(client, admin, alice, bob):
    admin_token = login(client, "admin")
    gpu_id, project_id = setup_resource(client, admin_token)
    server_id = client.get("/api/servers", headers={"Authorization": f"Bearer {admin_token}"}).json()[0]["id"]
    alice_t = login(client, "alice")
    bob_t = login(client, "bob")

    res = book(
        client,
        alice_t,
        gpu_ids=[gpu_id],
        mode="train",
        project_id=project_id,
        start="2026-06-02T10:00:00",
        end="2026-06-02T12:00:00",
    )
    assert res.status_code == 201
    for _ in range(4):
        res = book(
            client,
            bob_t,
            gpu_ids=[],
            mode="cpu",
            project_id=project_id,
            server_id=server_id,
            start="2026-06-02T10:00:00",
            end="2026-06-02T12:00:00",
        )
        assert res.status_code == 201


def test_conflict_on_second_gpu(client, admin, alice, bob):
    admin_token = login(client, "admin")
    gpu_id, project_id = setup_resource(client, admin_token)
    server_id = client.get("/api/servers", headers={"Authorization": f"Bearer {admin_token}"}).json()[0]["id"]
    gpu2 = create_gpu(client, server_id, "B100 #0", admin_token)

    alice_t = login(client, "alice")
    res = book(
        client,
        alice_t,
        gpu_ids=[gpu_id, gpu2["id"]],
        mode="train",
        project_id=project_id,
        start="2026-06-02T10:00:00",
        end="2026-06-02T12:00:00",
    )
    assert res.status_code == 201
    res = book(
        client,
        login(client, "bob"),
        gpu_ids=[gpu2["id"]],
        mode="train",
        project_id=project_id,
        start="2026-06-02T11:00:00",
        end="2026-06-02T13:00:00",
    )
    assert res.status_code == 409


def test_update_into_occupied_time_conflict(client, admin, alice, bob):
    admin_token = login(client, "admin")
    gpu_id, project_id = setup_resource(client, admin_token)
    alice_t = login(client, "alice")
    res = book(
        client,
        alice_t,
        gpu_ids=[gpu_id],
        mode="train",
        project_id=project_id,
        start="2026-06-02T10:00:00",
        end="2026-06-02T12:00:00",
    )
    booking_id = res.json()["id"]
    res = book(
        client,
        login(client, "bob"),
        gpu_ids=[gpu_id],
        mode="train",
        project_id=project_id,
        start="2026-06-02T11:00:00",
        end="2026-06-02T13:00:00",
    )
    assert res.status_code == 409
    res = book(
        client,
        login(client, "bob"),
        gpu_ids=[gpu_id],
        mode="train",
        project_id=project_id,
        start="2026-06-02T12:00:00",
        end="2026-06-02T14:00:00",
    )
    assert res.status_code == 201

    res = client.patch(
        f"/api/bookings/{booking_id}",
        json={
            "gpu_ids": [gpu_id],
            "mode": "train",
            "project_id": project_id,
            "start_at": "2026-06-02T13:00:00",
            "end_at": "2026-06-02T15:00:00",
            "description": None,
        },
        headers=auth_headers(client, "alice"),
    )
    assert res.status_code == 409

    res = client.patch(
        f"/api/bookings/{booking_id}",
        json={
            "gpu_ids": [gpu_id],
            "mode": "train",
            "project_id": project_id,
            "start_at": "2026-06-02T09:00:00",
            "end_at": "2026-06-02T10:00:00",
            "description": None,
        },
        headers=auth_headers(client, "alice"),
    )
    assert res.status_code == 200


def test_update_self_no_conflict(client, admin, alice):
    admin_token = login(client, "admin")
    gpu_id, project_id = setup_resource(client, admin_token)
    alice_t = login(client, "alice")
    res = book(
        client,
        alice_t,
        gpu_ids=[gpu_id],
        mode="train",
        project_id=project_id,
        start="2026-06-02T10:00:00",
        end="2026-06-02T12:00:00",
    )
    booking_id = res.json()["id"]
    res = client.patch(
        f"/api/bookings/{booking_id}",
        json={
            "gpu_ids": [gpu_id],
            "mode": "train",
            "project_id": project_id,
            "start_at": "2026-06-02T10:00:00",
            "end_at": "2026-06-02T13:00:00",
            "description": "verlängert",
        },
        headers=auth_headers(client, "alice"),
    )
    assert res.status_code == 200
    assert res.json()["end_at"].startswith("2026-06-02T13:00:00")


def test_update_reuses_unchanged_gpu_links_when_swapping_gpus(client, admin, alice):
    admin_token = login(client, "admin")
    server = create_server(client, "swap-cluster", admin_token)
    gpu1 = create_gpu(client, server["id"], "GPU #1", admin_token)
    gpu2 = create_gpu(client, server["id"], "GPU #2", admin_token)
    gpu3 = create_gpu(client, server["id"], "GPU #3", admin_token)
    project = create_project(client, "Swap-Projekt", admin_token)
    alice_token = login(client, "alice")

    created = book(
        client,
        alice_token,
        gpu_ids=[gpu1["id"], gpu2["id"]],
        mode="dev",
        project_id=project["id"],
        start="2026-06-02T10:00:00",
        end="2026-06-02T12:00:00",
    )

    res = client.patch(
        f"/api/bookings/{created.json()['id']}",
        json={
            "gpu_ids": [gpu2["id"], gpu3["id"]],
            "mode": "dev",
            "project_id": project["id"],
            "start_at": "2026-06-02T10:00:00",
            "end_at": "2026-06-02T12:00:00",
            "description": "GPU-Tausch",
        },
        headers={"Authorization": f"Bearer {alice_token}"},
    )

    assert res.status_code == 200
    assert {gpu["id"] for gpu in res.json()["gpus"]} == {gpu2["id"], gpu3["id"]}


def test_seven_day_limit_for_user(client, admin, alice):
    admin_token = login(client, "admin")
    gpu_id, project_id = setup_resource(client, admin_token)
    res = book(
        client,
        login(client, "alice"),
        gpu_ids=[gpu_id],
        mode="train",
        project_id=project_id,
        start="2026-06-01T00:00:00",
        end="2026-06-08T01:00:00",
    )
    assert res.status_code == 400
    assert "7 Tage" in res.json()["detail"]

    res = book(
        client,
        login(client, "alice"),
        gpu_ids=[gpu_id],
        mode="train",
        project_id=project_id,
        start="2026-06-01T00:00:00",
        end="2026-06-08T00:00:00",
    )
    assert res.status_code == 201


def test_configured_booking_limit_is_enforced(client, admin, alice, monkeypatch):
    monkeypatch.setattr(
        "app.services.bookings.get_settings",
        lambda: SimpleNamespace(max_booking_days=2),
    )
    admin_token = login(client, "admin")
    gpu_id, project_id = setup_resource(client, admin_token)
    alice_token = login(client, "alice")

    exact_limit = book(
        client,
        alice_token,
        gpu_ids=[gpu_id],
        mode="train",
        project_id=project_id,
        start="2026-06-01T00:00:00",
        end="2026-06-03T00:00:00",
    )
    assert exact_limit.status_code == 201

    over_limit = book(
        client,
        alice_token,
        gpu_ids=[gpu_id],
        mode="train",
        project_id=project_id,
        start="2026-06-04T00:00:00",
        end="2026-06-06T01:00:00",
    )
    assert over_limit.status_code == 400
    assert "2 Tage" in over_limit.json()["detail"]


def test_admin_unlimited(client, admin):
    admin_token = login(client, "admin")
    gpu_id, project_id = setup_resource(client, admin_token)
    res = book(
        client,
        admin_token,
        gpu_ids=[gpu_id],
        mode="train",
        project_id=project_id,
        start="2026-06-01T00:00:00",
        end="2026-06-09T00:00:00",
    )
    assert res.status_code == 201


def test_admin_can_extend_regular_users_booking_beyond_seven_days(client, admin, alice):
    admin_token = login(client, "admin")
    gpu_id, project_id = setup_resource(client, admin_token)
    created = book(
        client,
        login(client, "alice"),
        gpu_ids=[gpu_id],
        mode="dev",
        project_id=project_id,
        start="2026-06-01T00:00:00",
        end="2026-06-02T00:00:00",
    )

    res = client.patch(
        f"/api/bookings/{created.json()['id']}",
        json={
            "gpu_ids": [gpu_id],
            "mode": "dev",
            "project_id": project_id,
            "start_at": "2026-06-01T00:00:00",
            "end_at": "2026-06-09T00:00:00",
            "description": None,
        },
        headers={"Authorization": f"Bearer {admin_token}"},
    )

    assert res.status_code == 200


def test_backdating_allowed(client, admin, alice):
    admin_token = login(client, "admin")
    gpu_id, project_id = setup_resource(client, admin_token)
    res = book(
        client,
        login(client, "alice"),
        gpu_ids=[gpu_id],
        mode="dev",
        project_id=project_id,
        start="2020-01-01T00:00:00",
        end="2020-01-01T02:00:00",
    )
    assert res.status_code == 201


def test_edit_by_other_user_forbidden(client, admin, alice, bob):
    admin_token = login(client, "admin")
    gpu_id, project_id = setup_resource(client, admin_token)
    res = book(
        client,
        login(client, "alice"),
        gpu_ids=[gpu_id],
        mode="dev",
        project_id=project_id,
        start="2026-06-02T10:00:00",
        end="2026-06-02T12:00:00",
    )
    booking_id = res.json()["id"]
    res = client.patch(
        f"/api/bookings/{booking_id}",
        json={
            "gpu_ids": [gpu_id],
            "mode": "dev",
            "project_id": project_id,
            "start_at": "2026-06-02T10:00:00",
            "end_at": "2026-06-02T13:00:00",
            "description": None,
        },
        headers=auth_headers(client, "bob"),
    )
    assert res.status_code == 403

    res = client.patch(
        f"/api/bookings/{booking_id}",
        json={
            "gpu_ids": [gpu_id],
            "mode": "dev",
            "project_id": project_id,
            "start_at": "2026-06-02T10:00:00",
            "end_at": "2026-06-02T13:00:00",
            "description": None,
        },
        headers=auth_headers(client, "admin"),
    )
    assert res.status_code == 200


def test_delete_owner_or_admin(client, admin, alice, bob):
    admin_token = login(client, "admin")
    gpu_id, project_id = setup_resource(client, admin_token)
    owner_booking = book(
        client,
        login(client, "alice"),
        gpu_ids=[gpu_id],
        mode="dev",
        project_id=project_id,
        start="2026-06-02T10:00:00",
        end="2026-06-02T12:00:00",
    )
    assert owner_booking.status_code == 201
    owner_booking_id = owner_booking.json()["id"]

    owner_delete = client.delete(f"/api/bookings/{owner_booking_id}", headers=auth_headers(client, "alice"))
    assert owner_delete.status_code == 204

    admin_booking = book(
        client,
        login(client, "alice"),
        gpu_ids=[gpu_id],
        mode="dev",
        project_id=project_id,
        start="2026-06-02T10:00:00",
        end="2026-06-02T12:00:00",
    )
    assert admin_booking.status_code == 201
    admin_booking_id = admin_booking.json()["id"]

    forbidden = client.delete(f"/api/bookings/{admin_booking_id}", headers=auth_headers(client, "bob"))
    assert forbidden.status_code == 403
    admin_delete = client.delete(f"/api/bookings/{admin_booking_id}", headers=auth_headers(client, "admin"))
    assert admin_delete.status_code == 204


def test_week_filter(client, admin, alice):
    admin_token = login(client, "admin")
    gpu_id, project_id = setup_resource(client, admin_token)
    res = book(
        client,
        login(client, "alice"),
        gpu_ids=[gpu_id],
        mode="dev",
        project_id=project_id,
        start="2026-06-01T10:00:00",
        end="2026-06-01T12:00:00",
    )
    assert res.status_code == 201
    res = client.get(
        "/api/bookings?from=2026-06-01T00:00:00&to=2026-06-07T00:00:00",
        headers=auth_headers(client, "alice"),
    )
    assert res.status_code == 200
    assert len(res.json()) == 1
    res = client.get(
        "/api/bookings?from=2026-06-08T00:00:00&to=2026-06-14T00:00:00",
        headers=auth_headers(client, "alice"),
    )
    assert res.json() == []


def test_create_daily_booking_series(client, admin, alice):
    admin_token = login(client, "admin")
    gpu_id, project_id = setup_resource(client, admin_token)
    res = client.post(
        "/api/bookings/series",
        json={
            "gpu_ids": [gpu_id],
            "server_id": None,
            "mode": "train",
            "project_id": project_id,
            "intervals": [
                {"start_at": "2026-06-01T10:00:00", "end_at": "2026-06-01T16:00:00"},
                {"start_at": "2026-06-02T08:00:00", "end_at": "2026-06-02T16:00:00"},
                {"start_at": "2026-06-03T08:00:00", "end_at": "2026-06-03T12:00:00"},
            ],
            "series_start_at": "2026-06-01T10:00:00",
            "series_end_at": "2026-06-03T12:00:00",
            "daily_start_hour": 8,
            "daily_end_hour": 16,
            "description": "Tägliches Training",
        },
        headers=auth_headers(client, "alice"),
    )
    assert res.status_code == 201
    assert len({booking["series_id"] for booking in res.json()}) == 1
    assert res.json()[0]["series_start_at"] == "2026-06-01T10:00:00"
    assert [(booking["start_at"], booking["end_at"]) for booking in res.json()] == [
        ("2026-06-01T10:00:00", "2026-06-01T16:00:00"),
        ("2026-06-02T08:00:00", "2026-06-02T16:00:00"),
        ("2026-06-03T08:00:00", "2026-06-03T12:00:00"),
    ]


def test_booking_series_uses_configured_outer_range_limit(client, admin, alice, monkeypatch):
    monkeypatch.setattr(
        "app.services.bookings.get_settings",
        lambda: SimpleNamespace(max_booking_days=2),
    )
    admin_token = login(client, "admin")
    gpu_id, project_id = setup_resource(client, admin_token)

    res = client.post(
        "/api/bookings/series",
        json={
            "gpu_ids": [gpu_id],
            "server_id": None,
            "mode": "dev",
            "project_id": project_id,
            "intervals": [
                {"start_at": "2026-06-01T10:00:00", "end_at": "2026-06-01T11:00:00"},
                {"start_at": "2026-06-04T10:00:00", "end_at": "2026-06-04T11:00:00"},
            ],
            "series_start_at": "2026-06-01T10:00:00",
            "series_end_at": "2026-06-04T11:00:00",
            "daily_start_hour": 10,
            "daily_end_hour": 11,
            "description": None,
        },
        headers=auth_headers(client, "alice"),
    )

    assert res.status_code == 400
    assert "2 Tage" in res.json()["detail"]


def test_daily_booking_series_is_atomic_on_conflict(client, admin, alice):
    admin_token = login(client, "admin")
    gpu_id, project_id = setup_resource(client, admin_token)
    alice_token = login(client, "alice")
    existing = book(
        client,
        alice_token,
        gpu_ids=[gpu_id],
        mode="train",
        project_id=project_id,
        start="2026-06-02T10:00:00",
        end="2026-06-02T11:00:00",
    )
    assert existing.status_code == 201

    res = client.post(
        "/api/bookings/series",
        json={
            "gpu_ids": [gpu_id],
            "mode": "train",
            "project_id": project_id,
            "intervals": [
                {"start_at": "2026-06-01T08:00:00", "end_at": "2026-06-01T16:00:00"},
                {"start_at": "2026-06-02T08:00:00", "end_at": "2026-06-02T16:00:00"},
            ],
            "series_start_at": "2026-06-01T08:00:00",
            "series_end_at": "2026-06-02T16:00:00",
            "daily_start_hour": 8,
            "daily_end_hour": 16,
        },
        headers={"Authorization": f"Bearer {alice_token}"},
    )
    assert res.status_code == 409

    listed = client.get(
        "/api/bookings?from=2026-06-01T00:00:00&to=2026-06-03T00:00:00",
        headers={"Authorization": f"Bearer {alice_token}"},
    )
    assert len(listed.json()) == 1
    assert listed.json()[0]["id"] == existing.json()["id"]


def test_daily_booking_series_updates_and_deletes_as_group(client, admin, alice):
    admin_token = login(client, "admin")
    gpu_id, project_id = setup_resource(client, admin_token)
    headers = auth_headers(client, "alice")
    created = client.post(
        "/api/bookings/series",
        json={
            "gpu_ids": [gpu_id],
            "mode": "dev",
            "project_id": project_id,
            "intervals": [
                {"start_at": "2026-06-01T08:00:00", "end_at": "2026-06-01T16:00:00"},
                {"start_at": "2026-06-02T08:00:00", "end_at": "2026-06-02T16:00:00"},
            ],
            "series_start_at": "2026-06-01T08:00:00",
            "series_end_at": "2026-06-02T16:00:00",
            "daily_start_hour": 8,
            "daily_end_hour": 16,
        },
        headers=headers,
    )
    assert created.status_code == 201
    series_id = created.json()[0]["series_id"]

    updated = client.patch(
        f"/api/bookings/series/{series_id}",
        json={
            "gpu_ids": [gpu_id],
            "mode": "dev",
            "project_id": project_id,
            "intervals": [
                {"start_at": "2026-06-01T09:00:00", "end_at": "2026-06-01T15:00:00"},
                {"start_at": "2026-06-02T09:00:00", "end_at": "2026-06-02T15:00:00"},
                {"start_at": "2026-06-03T09:00:00", "end_at": "2026-06-03T15:00:00"},
            ],
            "series_start_at": "2026-06-01T09:00:00",
            "series_end_at": "2026-06-03T15:00:00",
            "daily_start_hour": 9,
            "daily_end_hour": 15,
        },
        headers=headers,
    )
    assert updated.status_code == 200
    assert len(updated.json()) == 3
    assert {booking["series_id"] for booking in updated.json()} == {series_id}
    assert {booking["start_at"][11:16] for booking in updated.json()} == {"09:00"}

    single_delete = client.delete(f"/api/bookings/{updated.json()[0]['id']}", headers=headers)
    assert single_delete.status_code == 409
    deleted = client.delete(f"/api/bookings/series/{series_id}", headers=headers)
    assert deleted.status_code == 204
    listed = client.get(
        "/api/bookings?from=2026-06-01T00:00:00&to=2026-06-04T00:00:00",
        headers=headers,
    )
    assert listed.json() == []


def test_inactive_gpu_rejected(client, admin, alice):
    admin_token = login(client, "admin")
    gpu_id, project_id = setup_resource(client, admin_token)
    client.patch(f"/api/gpus/{gpu_id}", json={"active": False}, headers=auth_headers(client, "admin"))
    res = book(
        client,
        login(client, "alice"),
        gpu_ids=[gpu_id],
        mode="dev",
        project_id=project_id,
        start="2026-06-02T10:00:00",
        end="2026-06-02T12:00:00",
    )
    assert res.status_code == 400
    assert "inaktiv" in res.json()["detail"]


def test_existing_booking_can_keep_deactivated_gpu(client, admin, alice):
    admin_token = login(client, "admin")
    gpu_id, project_id = setup_resource(client, admin_token)
    create_res = book(
        client,
        login(client, "alice"),
        gpu_ids=[gpu_id],
        mode="dev",
        project_id=project_id,
        start="2026-06-02T10:00:00",
        end="2026-06-02T12:00:00",
    )
    booking_id = create_res.json()["id"]
    client.patch(f"/api/gpus/{gpu_id}", json={"active": False}, headers=auth_headers(client, "admin"))

    res = client.patch(
        f"/api/bookings/{booking_id}",
        json={
            "gpu_ids": [gpu_id],
            "mode": "dev",
            "project_id": project_id,
            "start_at": "2026-06-02T10:00:00",
            "end_at": "2026-06-02T13:00:00",
            "description": "GPU inzwischen deaktiviert",
        },
        headers=auth_headers(client, "alice"),
    )
    assert res.status_code == 200
    assert res.json()["gpus"][0]["active"] is False


def test_inactive_project_rejected(client, admin, alice):
    admin_token = login(client, "admin")
    gpu_id, project_id = setup_resource(client, admin_token)
    client.patch(f"/api/projects/{project_id}", json={"active": False}, headers=auth_headers(client, "admin"))
    res = book(
        client,
        login(client, "alice"),
        gpu_ids=[gpu_id],
        mode="dev",
        project_id=project_id,
        start="2026-06-02T10:00:00",
        end="2026-06-02T12:00:00",
    )
    assert res.status_code == 400
    assert "inaktiv" in res.json()["detail"]


def test_filter_by_gpu_and_user(client, admin, alice, bob):
    admin_token = login(client, "admin")
    gpu_id, project_id = setup_resource(client, admin_token)
    alice_t = login(client, "alice")
    bob_t = login(client, "bob")
    book(
        client,
        alice_t,
        gpu_ids=[gpu_id],
        mode="dev",
        project_id=project_id,
        start="2026-06-01T10:00:00",
        end="2026-06-01T12:00:00",
    )
    book(
        client,
        bob_t,
        gpu_ids=[gpu_id],
        mode="dev",
        project_id=project_id,
        start="2026-06-01T12:00:00",
        end="2026-06-01T14:00:00",
    )

    res = client.get(
        "/api/bookings?from=2026-06-01T00:00:00&to=2026-06-02T00:00:00&user_id=2",
        headers=auth_headers(client, "alice"),
    )
    assert len(res.json()) == 1
    assert res.json()[0]["user"]["display_name"] == "alice"

    res = client.get(
        f"/api/bookings?from=2026-06-01T00:00:00&to=2026-06-02T00:00:00&gpu_id={gpu_id}",
        headers=auth_headers(client, "alice"),
    )
    assert len(res.json()) == 2
