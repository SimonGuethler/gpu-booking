"""Zeitstempel der letzten Passwortänderung (Session-Invalidierung).

Revision ID: 20260906_0005
Revises: 20260824_0004
Create Date: 2026-09-06
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260906_0005"
down_revision: str | None = "20260824_0004"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    bind = op.get_bind()
    columns = {column["name"] for column in sa.inspect(bind).get_columns("users")}
    if "password_changed_at" not in columns:
        # Bewusst ohne Backfill/Server-Default: NULL bedeutet "Anfangspasswort ist
        # noch in Kraft", damit bestehende Session-Cookies nach dem Deploy gültig
        # bleiben. Erst die nächste Passwortänderung setzt den Zeitstempel und
        # beendet dann alle davor ausgestellten Sessions.
        op.add_column("users", sa.Column("password_changed_at", sa.DateTime(), nullable=True))


def downgrade() -> None:
    bind = op.get_bind()
    columns = {column["name"] for column in sa.inspect(bind).get_columns("users")}
    if "password_changed_at" in columns:
        op.drop_column("users", "password_changed_at")
