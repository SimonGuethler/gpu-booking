import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from starlette.responses import JSONResponse

from app.config import get_settings
from app.database import SessionLocal, upgrade_db
from app.models import User
from app.routers import auth, bookings, config, projects, servers, users
from app.security import hash_password

logger = logging.getLogger(__name__)


def seed_admin() -> None:
    settings = get_settings()
    if not settings.seed_admin_password:
        return
    db = SessionLocal()
    try:
        if db.scalar(select(User.id).limit(1)) is not None:
            return
        if db.scalar(select(User).where(User.email == settings.seed_admin_email.strip().lower())):
            return
        db.add(
            User(
                display_name=settings.seed_admin_display_name.strip(),
                email=settings.seed_admin_email.strip().lower(),
                password_hash=hash_password(settings.seed_admin_password),
                role="admin",
                color="#8b5cf6",
            )
        )
        db.commit()
    finally:
        db.close()


@asynccontextmanager
async def lifespan(_: FastAPI):
    upgrade_db()
    seed_admin()
    yield


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(title="GPU-Buchungssystem", version="0.1.0", lifespan=lifespan)

    @app.exception_handler(IntegrityError)
    async def integrity_error_handler(request: Request, exc: IntegrityError) -> JSONResponse:
        logger.exception(
            "Datenbank-Integritätskonflikt bei %s %s",
            request.method,
            request.url.path,
            exc_info=exc,
        )
        return JSONResponse(
            status_code=409,
            content={"detail": "Der Datensatz steht im Konflikt mit einem vorhandenen Eintrag."},
        )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origin_list,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
        expose_headers=["X-CSRF-Token"],
    )

    api = "/api"
    app.include_router(auth.router, prefix=api)
    app.include_router(config.router, prefix=api)
    app.include_router(users.router, prefix=api)
    app.include_router(servers.router, prefix=api)
    app.include_router(projects.router, prefix=api)
    app.include_router(bookings.router, prefix=api)
    return app


app = create_app()
