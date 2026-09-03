"""Metadaten für zusammengehörige tägliche Buchungsserien.

Revision ID: 20260824_0004
Revises: 20260824_0003
Create Date: 2026-08-24
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260824_0004"
down_revision: str | None = "20260824_0003"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    columns = {column["name"] for column in inspector.get_columns("bookings")}
    indexes = {index["name"] for index in inspector.get_indexes("bookings")}
    with op.batch_alter_table("bookings") as batch_op:
        if "series_id" not in columns:
            batch_op.add_column(sa.Column("series_id", sa.String(length=36), nullable=True))
        if "series_start_at" not in columns:
            batch_op.add_column(sa.Column("series_start_at", sa.DateTime(), nullable=True))
        if "series_end_at" not in columns:
            batch_op.add_column(sa.Column("series_end_at", sa.DateTime(), nullable=True))
        if "daily_start_hour" not in columns:
            batch_op.add_column(sa.Column("daily_start_hour", sa.Integer(), nullable=True))
        if "daily_end_hour" not in columns:
            batch_op.add_column(sa.Column("daily_end_hour", sa.Integer(), nullable=True))
        if "ix_bookings_series_id" not in indexes:
            batch_op.create_index("ix_bookings_series_id", ["series_id"], unique=False)


def downgrade() -> None:
    with op.batch_alter_table("bookings") as batch_op:
        batch_op.drop_index("ix_bookings_series_id")
        batch_op.drop_column("daily_end_hour")
        batch_op.drop_column("daily_start_hour")
        batch_op.drop_column("series_end_at")
        batch_op.drop_column("series_start_at")
        batch_op.drop_column("series_id")
