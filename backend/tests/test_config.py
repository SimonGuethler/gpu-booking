import pytest
from pydantic import ValidationError

from app.config import Settings
from tests.conftest import login


def test_config_requires_authentication(client):
    assert client.get("/api/config").status_code == 401


def test_cors_wildcard_origin_is_rejected():
    with pytest.raises(ValidationError, match="CORS_ORIGINS"):
        Settings(_env_file=None, cors_origins="*")


def test_cors_wildcard_between_origins_is_rejected():
    with pytest.raises(ValidationError, match="CORS_ORIGINS"):
        Settings(_env_file=None, cors_origins="http://a.local, , *")


def test_cors_origins_still_accept_concrete_origins():
    settings = Settings(_env_file=None, cors_origins="http://a.local:5173, http://a.local:80")
    assert settings.cors_origin_list == ["http://a.local:5173", "http://a.local:80"]


def test_config_returns_booking_limit(client, alice):
    token = login(client, "alice")
    response = client.get(
        "/api/config",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 200
    assert response.json() == {"max_booking_days": 7, "gpu_memory_mb_max": 2**31}


def test_max_booking_days_is_read_from_environment(monkeypatch):
    monkeypatch.setenv("MAX_BOOKING_DAYS", "3")

    assert Settings(_env_file=None).max_booking_days == 3
