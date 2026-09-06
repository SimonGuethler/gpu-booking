import sqlite3

import pytest
from sqlalchemy.exc import OperationalError

from app.database import create_app_engine


def test_sqlite_serializes_write_transactions(tmp_path):
    engine = create_app_engine(f"sqlite:///{tmp_path / 'serial.db'}", connect_args_override={"timeout": 0.1})

    conn_holding = engine.connect()
    # BEGIN IMMEDIATE hält die Schreibsperre ab Transaktionsbeginn (nicht erst
    # beim ersten Write), damit eine parallele Transaktion nicht ihre
    # Konfliktprüfung auf einem veralteten Snapshot ausführt.
    _trans_holding = conn_holding.begin()
    conn_waiting = engine.connect()
    try:
        with pytest.raises((OperationalError, sqlite3.OperationalError), match="locked"):
            conn_waiting.begin()
        _trans_holding.commit()

        # Nach dem Commit ist die Sperre wieder frei, kein „database is locked“.
        waiting_transaction = conn_waiting.begin()
        waiting_transaction.commit()
    finally:
        conn_holding.close()
        conn_waiting.close()
