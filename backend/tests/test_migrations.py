from datetime import datetime

import sqlalchemy as sa
from alembic import command

from app.database import Base, alembic_config


def _upgrade(engine: sa.Engine) -> None:
    config = alembic_config()
    with engine.connect() as connection:
        config.attributes["connection"] = connection
        command.upgrade(config, "head")


def _legacy_metadata() -> sa.MetaData:
    metadata = sa.MetaData()
    sa.Table(
        "users",
        metadata,
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("username", sa.String(80), nullable=False),
        sa.Column("email", sa.String(255), nullable=False),
        sa.Column("password_hash", sa.String(255), nullable=False),
        sa.Column("role", sa.String(10), nullable=False),
        sa.Column("color", sa.String(9), nullable=False),
        sa.Column("created_at", sa.DateTime, nullable=False),
    )
    sa.Table(
        "servers",
        metadata,
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("name", sa.String(120), nullable=False),
        sa.Column("hostname", sa.String(255)),
        sa.Column("active", sa.Boolean, nullable=False),
        sa.Column("created_at", sa.DateTime, nullable=False),
    )
    sa.Table(
        "projects",
        metadata,
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("name", sa.String(120), nullable=False),
        sa.Column("description", sa.Text),
        sa.Column("owner_id", sa.ForeignKey("users.id"), nullable=False),
        sa.Column("active", sa.Boolean, nullable=False),
        sa.Column("created_at", sa.DateTime, nullable=False),
    )
    sa.Table(
        "gpus",
        metadata,
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("server_id", sa.ForeignKey("servers.id"), nullable=False),
        sa.Column("name", sa.String(120), nullable=False),
        sa.Column("memory_mb", sa.Integer),
        sa.Column("active", sa.Boolean, nullable=False),
        sa.Column("created_at", sa.DateTime, nullable=False),
    )
    sa.Table(
        "project_members",
        metadata,
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("project_id", sa.ForeignKey("projects.id"), nullable=False),
        sa.Column("user_id", sa.ForeignKey("users.id"), nullable=False),
    )
    sa.Table(
        "bookings",
        metadata,
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("user_id", sa.ForeignKey("users.id"), nullable=False),
        sa.Column("project_id", sa.ForeignKey("projects.id"), nullable=False),
        sa.Column("start_at", sa.DateTime, nullable=False),
        sa.Column("end_at", sa.DateTime, nullable=False),
        sa.Column("mode", sa.String(10), nullable=False),
        sa.Column("description", sa.Text),
        sa.Column("created_at", sa.DateTime, nullable=False),
        sa.Column("updated_at", sa.DateTime, nullable=False),
    )
    sa.Table(
        "booking_gpus",
        metadata,
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("booking_id", sa.ForeignKey("bookings.id"), nullable=False),
        sa.Column("gpu_id", sa.ForeignKey("gpus.id"), nullable=False),
    )
    return metadata


def test_fresh_migration_matches_model_metadata(tmp_path):
    engine = sa.create_engine(f"sqlite:///{tmp_path / 'fresh.db'}")
    _upgrade(engine)

    config = alembic_config()
    with engine.connect() as connection:
        config.attributes["connection"] = connection
        command.check(config)


def test_current_unversioned_database_is_adopted(tmp_path):
    engine = sa.create_engine(f"sqlite:///{tmp_path / 'current.db'}")
    Base.metadata.create_all(engine)

    _upgrade(engine)

    with engine.connect() as connection:
        revision = connection.scalar(sa.text("SELECT version_num FROM alembic_version"))
    assert revision == "20260824_0004"


def test_known_legacy_database_is_upgraded_without_data_loss(tmp_path):
    engine = sa.create_engine(f"sqlite:///{tmp_path / 'legacy.db'}")
    legacy = _legacy_metadata()
    legacy.create_all(engine)
    with engine.begin() as connection:
        connection.execute(
            legacy.tables["users"].insert(),
            {
                "id": 1,
                "username": "Alice",
                "email": "alice@example.local",
                "password_hash": "hash",
                "role": "user",
                "color": "#01adb9",
                "created_at": datetime(2026, 1, 1),
            },
        )

    _upgrade(engine)

    inspector = sa.inspect(engine)
    assert "display_name" in {column["name"] for column in inspector.get_columns("users")}
    assert "approved" in {column["name"] for column in inspector.get_columns("users")}
    assert "active" in {column["name"] for column in inspector.get_columns("users")}
    assert "server_id" in {column["name"] for column in inspector.get_columns("bookings")}
    booking_columns = {column["name"] for column in inspector.get_columns("bookings")}
    assert {
        "series_id",
        "series_start_at",
        "series_end_at",
        "daily_start_hour",
        "daily_end_hour",
    } <= booking_columns
    with engine.connect() as connection:
        row = connection.execute(
            sa.text("SELECT display_name, approved, active FROM users WHERE id = 1")
        ).one()
    assert row == ("Alice", 1, 1)
