from app.config import Settings
from tests.conftest import login


def test_config_requires_authentication(client):
    assert client.get("/api/config").status_code == 401


def test_config_returns_booking_limit(client, alice):
    token = login(client, "alice")
    response = client.get(
        "/api/config",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 200
    assert response.json() == {"max_booking_days": 7}


def test_max_booking_days_is_read_from_environment(monkeypatch):
    monkeypatch.setenv("MAX_BOOKING_DAYS", "3")

    assert Settings(_env_file=None).max_booking_days == 3
