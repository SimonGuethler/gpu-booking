"""Aktuelles Schema als Alembic-Baseline.

Revision ID: 20260822_0001
Revises:
Create Date: 2026-08-22
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import context, op

revision: str = "20260822_0001"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

APP_TABLES = {
    "users",
    "servers",
    "gpus",
    "projects",
    "project_members",
    "bookings",
    "booking_gpus",
}

REQUIRED_COLUMNS = {
    "users": {"id", "display_name", "email", "password_hash", "role", "color", "created_at"},
    "servers": {"id", "name", "hostname", "active", "created_at"},
    "gpus": {"id", "server_id", "name", "memory_mb", "active", "created_at"},
    "projects": {"id", "name", "description", "owner_id", "active", "created_at"},
    "project_members": {"id", "project_id", "user_id"},
    "bookings": {
        "id",
        "user_id",
        "project_id",
        "server_id",
        "start_at",
        "end_at",
        "mode",
        "description",
        "created_at",
        "updated_at",
    },
    "booking_gpus": {"id", "booking_id", "gpu_id"},
}

BATCH_NAMING_CONVENTION = {
    "ix": "ix_%(table_name)s_%(column_0_name)s",
    "uq": "uq_%(table_name)s_%(column_0_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s",
}


def _create_current_schema() -> None:
    op.create_table(
        "users",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("display_name", sa.String(length=80), nullable=False),
        sa.Column("email", sa.String(length=255), nullable=False),
        sa.Column("password_hash", sa.String(length=255), nullable=False),
        sa.Column("role", sa.String(length=10), nullable=False),
        sa.Column("color", sa.String(length=9), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id", name="pk_users"),
    )
    op.create_index("ix_users_display_name", "users", ["display_name"], unique=True)
    op.create_index("ix_users_email", "users", ["email"], unique=True)

    op.create_table(
        "servers",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("hostname", sa.String(length=255), nullable=True),
        sa.Column("active", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id", name="pk_servers"),
        sa.UniqueConstraint("name", name="uq_servers_name"),
    )

    op.create_table(
        "projects",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("owner_id", sa.Integer(), nullable=False),
        sa.Column("active", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["owner_id"], ["users.id"], name="fk_projects_owner_id_users"),
        sa.PrimaryKeyConstraint("id", name="pk_projects"),
        sa.UniqueConstraint("name", name="uq_projects_name"),
    )
    op.create_index("ix_projects_owner_id", "projects", ["owner_id"], unique=False)

    op.create_table(
        "gpus",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("server_id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("memory_mb", sa.Integer(), nullable=True),
        sa.Column("active", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(
            ["server_id"], ["servers.id"], name="fk_gpus_server_id_servers", ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id", name="pk_gpus"),
    )
    op.create_index("ix_gpus_server_id", "gpus", ["server_id"], unique=False)

    op.create_table(
        "project_members",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("project_id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(
            ["project_id"],
            ["projects.id"],
            name="fk_project_members_project_id_projects",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], name="fk_project_members_user_id_users"),
        sa.PrimaryKeyConstraint("id", name="pk_project_members"),
        sa.UniqueConstraint("project_id", "user_id", name="uq_project_members_project_id"),
    )
    op.create_index("ix_project_members_project_id", "project_members", ["project_id"], unique=False)
    op.create_index("ix_project_members_user_id", "project_members", ["user_id"], unique=False)

    op.create_table(
        "bookings",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("project_id", sa.Integer(), nullable=False),
        sa.Column("server_id", sa.Integer(), nullable=True),
        sa.Column("start_at", sa.DateTime(), nullable=False),
        sa.Column("end_at", sa.DateTime(), nullable=False),
        sa.Column("mode", sa.String(length=10), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"], name="fk_bookings_project_id_projects"),
        sa.ForeignKeyConstraint(
            ["server_id"],
            ["servers.id"],
            name="fk_bookings_server_id_servers",
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], name="fk_bookings_user_id_users"),
        sa.PrimaryKeyConstraint("id", name="pk_bookings"),
    )
    op.create_index("ix_bookings_project_id", "bookings", ["project_id"], unique=False)
    op.create_index("ix_bookings_server_id", "bookings", ["server_id"], unique=False)
    op.create_index("ix_bookings_start_at", "bookings", ["start_at"], unique=False)
    op.create_index("ix_bookings_user_id", "bookings", ["user_id"], unique=False)

    op.create_table(
        "booking_gpus",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("booking_id", sa.Integer(), nullable=False),
        sa.Column("gpu_id", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(
            ["booking_id"],
            ["bookings.id"],
            name="fk_booking_gpus_booking_id_bookings",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(["gpu_id"], ["gpus.id"], name="fk_booking_gpus_gpu_id_gpus"),
        sa.PrimaryKeyConstraint("id", name="pk_booking_gpus"),
        sa.UniqueConstraint("booking_id", "gpu_id", name="uq_booking_gpus_booking_id"),
    )
    op.create_index("ix_booking_gpus_booking_id", "booking_gpus", ["booking_id"], unique=False)
    op.create_index("ix_booking_gpus_gpu_id", "booking_gpus", ["gpu_id"], unique=False)


def _upgrade_known_existing_schema(bind) -> None:
    inspector = sa.inspect(bind)
    tables = set(inspector.get_table_names())
    missing_tables = APP_TABLES - tables
    if missing_tables:
        missing = ", ".join(sorted(missing_tables))
        raise RuntimeError(f"Unvollständiges Legacy-Schema; fehlende Tabellen: {missing}")

    user_columns = {column["name"] for column in inspector.get_columns("users")}
    if "display_name" not in user_columns:
        if "username" not in user_columns:
            raise RuntimeError("Legacy-Schema enthält weder users.display_name noch users.username.")
        op.alter_column(
            "users",
            "username",
            new_column_name="display_name",
            existing_type=sa.String(length=80),
            existing_nullable=False,
        )

    inspector = sa.inspect(bind)
    user_indexes = {index["name"] for index in inspector.get_indexes("users")}
    if "ix_users_username" in user_indexes:
        op.drop_index("ix_users_username", table_name="users")
        user_indexes.remove("ix_users_username")
    if "ix_users_display_name" not in user_indexes:
        op.create_index("ix_users_display_name", "users", ["display_name"], unique=True)

    booking_columns = {column["name"] for column in inspector.get_columns("bookings")}
    if "server_id" not in booking_columns:
        with op.batch_alter_table("bookings", naming_convention=BATCH_NAMING_CONVENTION) as batch_op:
            batch_op.add_column(sa.Column("server_id", sa.Integer(), nullable=True))
            batch_op.create_foreign_key(
                "fk_bookings_server_id_servers",
                "servers",
                ["server_id"],
                ["id"],
                ondelete="SET NULL",
            )
            batch_op.create_index("ix_bookings_server_id", ["server_id"], unique=False)
    else:
        booking_indexes = {index["name"] for index in inspector.get_indexes("bookings")}
        if "ix_bookings_server_id" not in booking_indexes:
            op.create_index("ix_bookings_server_id", "bookings", ["server_id"], unique=False)

    inspector = sa.inspect(bind)
    for table, required in REQUIRED_COLUMNS.items():
        columns = {column["name"] for column in inspector.get_columns(table)}
        missing_columns = required - columns
        if missing_columns:
            missing = ", ".join(sorted(missing_columns))
            raise RuntimeError(f"Unvollständiges Legacy-Schema in {table}; fehlende Spalten: {missing}")


def upgrade() -> None:
    if context.is_offline_mode():
        _create_current_schema()
        return
    bind = op.get_bind()
    existing_app_tables = APP_TABLES & set(sa.inspect(bind).get_table_names())
    if not existing_app_tables:
        _create_current_schema()
        return
    _upgrade_known_existing_schema(bind)


def downgrade() -> None:
    op.drop_table("booking_gpus")
    op.drop_table("bookings")
    op.drop_table("project_members")
    op.drop_table("gpus")
    op.drop_table("projects")
    op.drop_table("servers")
    op.drop_table("users")
