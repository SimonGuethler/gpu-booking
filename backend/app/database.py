import sqlite3
from collections.abc import Generator
from pathlib import Path

from alembic import command
from alembic.config import Config
from sqlalchemy import Engine, MetaData, create_engine, event
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.config import get_settings

NAMING_CONVENTION = {
    "ix": "ix_%(table_name)s_%(column_0_name)s",
    "uq": "uq_%(table_name)s_%(column_0_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s",
}


class Base(DeclarativeBase):
    metadata = MetaData(naming_convention=NAMING_CONVENTION)


def _engine_kwargs(url: str) -> dict:
    kwargs: dict = {"pool_pre_ping": True}
    if url.startswith("sqlite"):
        kwargs["connect_args"] = {"check_same_thread": False}
    return kwargs


# SQLite erzwingt Fremdschlüssel nur pro Verbindung; ohne das PRAGMA greifen
# ON DELETE/SET NULL-Regeln dort nicht wie in Postgres.
@event.listens_for(Engine, "connect")
def _enable_sqlite_foreign_keys(dbapi_connection, _connection_record) -> None:
    if isinstance(dbapi_connection, sqlite3.Connection):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()


def _enable_sqlite_write_locks(engine: Engine) -> None:
    """SQLite serialisiert Schreibtransaktionen per BEGIN IMMEDIATE.

    Ohne das können zwei parallele Buchungen beide die Konfliktprüfung auf dem
    selben Snapshot ausführen und nacheinander einbuchen (SQLite ignoriert
    FOR UPDATE); mit BEGIN IMMEDIATE wartet die zweite Transaktion auf die
    Schreibsperre und sieht danach die erste Buchung. Nur für SQLite-Engines
    gedacht; der offizielle SQLAlchemy-Rezept (Dialect-Doku „Serializable
    isolation“): sqlite3 übernimmt die BEGIN-Steuerung komplett.
    """

    @event.listens_for(engine, "connect")
    def _disable_dbapi_begin(dbapi_connection, _connection_record) -> None:
        dbapi_connection.isolation_level = None

    @event.listens_for(engine, "begin")
    def _begin_immediate(connection) -> None:
        connection.exec_driver_sql("BEGIN IMMEDIATE")


def create_app_engine(database_url: str, connect_args_override: dict | None = None) -> Engine:
    kwargs = _engine_kwargs(database_url)
    if connect_args_override:
        merged = kwargs.get("connect_args", {})
        kwargs["connect_args"] = {**merged, **connect_args_override}
    new_engine = create_engine(database_url, **kwargs)
    if database_url.startswith("sqlite"):
        _enable_sqlite_write_locks(new_engine)
    return new_engine


engine = create_app_engine(get_settings().database_url)
SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def alembic_config() -> Config:
    backend_dir = Path(__file__).resolve().parent.parent
    config = Config(backend_dir / "alembic.ini")
    config.set_main_option("script_location", str(backend_dir / "migrations"))
    return config


def upgrade_db() -> None:
    config = alembic_config()
    with engine.connect() as connection:
        config.attributes["connection"] = connection
        command.upgrade(config, "head")
