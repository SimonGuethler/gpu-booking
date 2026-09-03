import os

os.environ["DATABASE_URL"] = "sqlite://"
os.environ["JWT_SECRET"] = "test-secret-test-secret-test-secret-123"
os.environ["JWT_EXPIRE_DAYS"] = "90"
os.environ["SEED_ADMIN_PASSWORD"] = ""

import pytest
from alembic import command
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.database import alembic_config, get_db
from app.main import create_app
from app.models import User
from app.security import AUTH_COOKIE_NAME, hash_password

engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
TestingSessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)

PASSWORD = "password123"


@pytest.fixture(autouse=True)
def _fresh_db():
    config = alembic_config()
    with engine.connect() as connection:
        config.attributes["connection"] = connection
        command.upgrade(config, "head")
    yield
    config = alembic_config()
    with engine.connect() as connection:
        config.attributes["connection"] = connection
        command.downgrade(config, "base")


def _override_db():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


@pytest.fixture
def client() -> TestClient:
    app = create_app()
    app.dependency_overrides[get_db] = _override_db
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture
def db():
    session = TestingSessionLocal()
    yield session
    session.close()


def create_user(
    db, display_name: str, role: str = "user", color: str | None = None, password: str = PASSWORD
) -> User:
    user = User(
        display_name=display_name,
        email=f"{display_name.lower()}@example.local",
        password_hash=hash_password(password),
        role=role,
        color=color or "#8b5cf6",
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@pytest.fixture
def admin(db) -> User:
    return create_user(db, "admin", role="admin")


@pytest.fixture
def alice(db) -> User:
    return create_user(db, "alice", role="user", color="#06b6d4")


@pytest.fixture
def bob(db) -> User:
    return create_user(db, "bob", role="user", color="#10b981")


def login(client: TestClient, account: str = "alice", password: str = PASSWORD) -> str:
    email = account if "@" in account else f"{account}@example.local"
    res = client.post("/api/auth/login", json={"email": email, "password": password})
    assert res.status_code == 200, res.text
    token = res.cookies.get(AUTH_COOKIE_NAME)
    assert token
    return token


def auth_headers(client: TestClient, account: str = "alice", password: str = PASSWORD) -> dict[str, str]:
    return {"Authorization": f"Bearer {login(client, account, password)}"}


def create_server(client: TestClient, name: str, token: str) -> dict:
    res = client.post(
        "/api/servers",
        json={"name": name, "hostname": f"{name}.local"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert res.status_code == 201, res.text
    return res.json()


def create_gpu(client: TestClient, server_id: int, name: str, token: str) -> dict:
    res = client.post(
        f"/api/servers/{server_id}/gpus",
        json={"name": name, "memory_mb": 49152},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert res.status_code == 201, res.text
    return res.json()


def create_project(
    client: TestClient,
    name: str,
    token: str,
    member_ids: list[int] | None = None,
) -> dict:
    res = client.post(
        "/api/projects",
        json={"name": name, "description": "Testprojekt", "member_ids": member_ids or []},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert res.status_code == 201, res.text
    return res.json()


def book(
    client: TestClient,
    token: str,
    *,
    gpu_ids: list[int],
    mode: str,
    project_id: int,
    start: str,
    end: str,
    server_id: int | None = None,
):
    return client.post(
        "/api/bookings",
        json={
            "gpu_ids": gpu_ids,
            "server_id": server_id,
            "mode": mode,
            "project_id": project_id,
            "start_at": start,
            "end_at": end,
            "description": None,
        },
        headers={"Authorization": f"Bearer {token}"},
    )
