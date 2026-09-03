from datetime import datetime
from typing import TypedDict
from uuid import uuid4

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app import models
from app.config import get_settings
from app.models import MODE_CPU, MODE_TRAIN

MODE_LABELS = {
    models.MODE_TRAIN: "Vollbelegung",
    models.MODE_DEV: "Teilbelegung",
    models.MODE_CPU: "CPU",
}


class BookingConflict(TypedDict):
    code: str
    message: str
    start_at: str
    end_at: str


def validate_input(
    db: Session,
    *,
    mode: str,
    project_id: int,
    server_id: int | None,
    gpu_ids: list[int],
    start_at: datetime,
    end_at: datetime,
    is_admin: bool,
    allowed_inactive_gpu_ids: set[int] | None = None,
    allowed_inactive_project_id: int | None = None,
    allowed_inactive_server_id: int | None = None,
) -> tuple[list[models.Gpu], models.Server | None]:
    allowed_inactive_gpu_ids = allowed_inactive_gpu_ids or set()
    duration_hours = (end_at - start_at).total_seconds() / 3600
    max_booking_days = get_settings().max_booking_days
    max_booking_hours = max_booking_days * 24
    if not is_admin and duration_hours > max_booking_hours:
        raise HTTPException(
            status_code=400,
            detail=f"Maximale Dauer einer Buchung ist {max_booking_hours} Stunden "
            f"({max_booking_days} Tage) – außer für Admins.",
        )

    project = db.get(models.Project, project_id)
    if project is None:
        raise HTTPException(status_code=400, detail="Das gewählte Projekt existiert nicht.")
    if not project.active and project.id != allowed_inactive_project_id:
        raise HTTPException(status_code=400, detail="Das gewählte Projekt ist inaktiv.")

    if mode == "cpu":
        server = db.get(models.Server, server_id)
        if server is None:
            raise HTTPException(status_code=400, detail="Der gewählte Server existiert nicht.")
        if not server.active and server.id != allowed_inactive_server_id:
            raise HTTPException(status_code=400, detail="Der gewählte Server ist inaktiv.")
        return [], server

    if len(set(gpu_ids)) != len(gpu_ids):
        raise HTTPException(status_code=400, detail="GPU-IDs dürfen nicht doppelt vorkommen.")

    gpus = db.scalars(select(models.Gpu).where(models.Gpu.id.in_(gpu_ids))).all()
    if len(gpus) != len(gpu_ids):
        raise HTTPException(status_code=400, detail="Mindestens eine gewählte GPU existiert nicht.")

    if len({gpu.server_id for gpu in gpus}) > 1:
        raise HTTPException(
            status_code=400,
            detail="Alle gewählten GPUs müssen zum selben Server gehören.",
        )

    for gpu in gpus:
        if (not gpu.active or not gpu.server.active) and gpu.id not in allowed_inactive_gpu_ids:
            raise HTTPException(
                status_code=400,
                detail=f"GPU {gpu.name} ist inaktiv und kann nicht belegt werden.",
            )
    return list(gpus), None


def _find_conflict(
    db: Session,
    gpu_ids: list[int],
    start_at: datetime,
    end_at: datetime,
    mode: str,
    exclude_booking_ids: set[int] | None,
) -> BookingConflict | None:
    if mode == MODE_CPU or not gpu_ids:
        return None

    stmt = (
        select(
            models.Booking.start_at,
            models.Booking.end_at,
            models.Booking.mode,
            models.Gpu.name,
            models.User.display_name,
        )
        .join(models.BookingGpu, models.BookingGpu.booking_id == models.Booking.id)
        .join(models.Gpu, models.Gpu.id == models.BookingGpu.gpu_id)
        .join(models.User, models.User.id == models.Booking.user_id)
        .where(models.Gpu.id.in_(gpu_ids))
        .where(models.Booking.start_at < end_at, models.Booking.end_at > start_at)
    )
    if exclude_booking_ids:
        stmt = stmt.where(models.Booking.id.not_in(exclude_booking_ids))
    if mode != MODE_TRAIN:
        stmt = stmt.where(models.Booking.mode == MODE_TRAIN)

    conflict = db.execute(
        stmt.order_by(models.Booking.start_at, models.Booking.id, models.Gpu.id).limit(1)
    ).one_or_none()
    if conflict is None:
        return None

    existing_start, existing_end, existing_mode, gpu_name, user_name = conflict
    other = f"{user_name} ({MODE_LABELS[existing_mode]})"
    return {
        "code": "booking_conflict",
        "message": f"Konflikt: {MODE_LABELS[mode]} überlappt mit {other} auf GPU {gpu_name}.",
        "start_at": existing_start.isoformat(),
        "end_at": existing_end.isoformat(),
    }


def _lock_gpus(db: Session, gpu_ids: list[int]) -> None:
    """Serialisiert parallele Buchungen auf denselben GPUs."""
    if gpu_ids:
        # Einheitliche Sperrreihenfolge vermeidet Deadlocks unter PostgreSQL.
        # SQLite ignoriert FOR UPDATE; dort bietet diese Sperre keine Parallelitätsgarantie.
        db.execute(
            select(models.Gpu.id).where(models.Gpu.id.in_(gpu_ids)).order_by(models.Gpu.id).with_for_update()
        )


def create_booking(
    db: Session,
    *,
    user: models.User,
    mode: str,
    project_id: int,
    server_id: int | None,
    gpu_ids: list[int],
    start_at: datetime,
    end_at: datetime,
    description: str | None,
) -> models.Booking:
    gpus, server = validate_input(
        db,
        mode=mode,
        project_id=project_id,
        server_id=server_id,
        gpu_ids=gpu_ids,
        start_at=start_at,
        end_at=end_at,
        is_admin=user.role == "admin",
    )
    _lock_gpus(db, [gpu.id for gpu in gpus])

    conflict = _find_conflict(db, [gpu.id for gpu in gpus], start_at, end_at, mode, None)
    if conflict:
        db.rollback()
        raise HTTPException(status_code=409, detail=conflict)

    booking = models.Booking(
        user_id=user.id,
        project_id=project_id,
        server_id=server.id if server else None,
        mode=mode,
        start_at=start_at,
        end_at=end_at,
        description=description,
    )
    db.add(booking)
    db.flush()
    for gpu in gpus:
        db.add(models.BookingGpu(booking_id=booking.id, gpu_id=gpu.id))
    db.commit()
    db.refresh(booking)
    return booking


def create_booking_series(
    db: Session,
    *,
    user: models.User,
    mode: str,
    project_id: int,
    server_id: int | None,
    gpu_ids: list[int],
    intervals: list[tuple[datetime, datetime]],
    series_start_at: datetime,
    series_end_at: datetime,
    daily_start_hour: int,
    daily_end_hour: int,
    description: str | None,
) -> list[models.Booking]:
    """Erstellt mehrere Tagesfenster atomar mit gemeinsamen Buchungsdaten."""
    gpus, server = validate_input(
        db,
        mode=mode,
        project_id=project_id,
        server_id=server_id,
        gpu_ids=gpu_ids,
        start_at=series_start_at,
        end_at=series_end_at,
        is_admin=user.role == "admin",
    )
    selected_gpu_ids = [gpu.id for gpu in gpus]
    _lock_gpus(db, selected_gpu_ids)

    for start_at, end_at in intervals:
        conflict = _find_conflict(db, selected_gpu_ids, start_at, end_at, mode, None)
        if conflict:
            db.rollback()
            raise HTTPException(status_code=409, detail=conflict)

    series_id = str(uuid4())
    bookings: list[models.Booking] = []
    for start_at, end_at in intervals:
        booking = models.Booking(
            user_id=user.id,
            project_id=project_id,
            server_id=server.id if server else None,
            mode=mode,
            start_at=start_at,
            end_at=end_at,
            series_id=series_id,
            series_start_at=series_start_at,
            series_end_at=series_end_at,
            daily_start_hour=daily_start_hour,
            daily_end_hour=daily_end_hour,
            description=description,
        )
        booking.gpus = [models.BookingGpu(gpu_id=gpu.id) for gpu in gpus]
        db.add(booking)
        bookings.append(booking)

    db.commit()
    for booking in bookings:
        db.refresh(booking)
    return bookings


def update_booking_series(
    db: Session,
    *,
    bookings: list[models.Booking],
    actor: models.User,
    mode: str,
    project_id: int,
    server_id: int | None,
    gpu_ids: list[int],
    intervals: list[tuple[datetime, datetime]],
    series_start_at: datetime,
    series_end_at: datetime,
    daily_start_hour: int,
    daily_end_hour: int,
    description: str | None,
) -> list[models.Booking]:
    first_booking = bookings[0]
    series_id = first_booking.series_id
    assert series_id is not None
    existing_ids = {booking.id for booking in bookings}
    existing_gpu_ids = {link.gpu_id for booking in bookings for link in booking.gpus}
    gpus, server = validate_input(
        db,
        mode=mode,
        project_id=project_id,
        server_id=server_id,
        gpu_ids=gpu_ids,
        start_at=series_start_at,
        end_at=series_end_at,
        is_admin=actor.role == "admin",
        allowed_inactive_gpu_ids=existing_gpu_ids,
        allowed_inactive_project_id=first_booking.project_id,
        allowed_inactive_server_id=first_booking.server_id,
    )
    selected_gpu_ids = [gpu.id for gpu in gpus]
    _lock_gpus(db, selected_gpu_ids)
    for start_at, end_at in intervals:
        conflict = _find_conflict(
            db,
            selected_gpu_ids,
            start_at,
            end_at,
            mode,
            existing_ids,
        )
        if conflict:
            db.rollback()
            raise HTTPException(status_code=409, detail=conflict)

    user_id = first_booking.user_id
    for booking in bookings:
        db.delete(booking)
    replacements: list[models.Booking] = []
    for start_at, end_at in intervals:
        replacement = models.Booking(
            user_id=user_id,
            project_id=project_id,
            server_id=server.id if server else None,
            mode=mode,
            start_at=start_at,
            end_at=end_at,
            series_id=series_id,
            series_start_at=series_start_at,
            series_end_at=series_end_at,
            daily_start_hour=daily_start_hour,
            daily_end_hour=daily_end_hour,
            description=description,
            gpus=[models.BookingGpu(gpu_id=gpu.id) for gpu in gpus],
        )
        db.add(replacement)
        replacements.append(replacement)
    db.commit()
    for replacement in replacements:
        db.refresh(replacement)
    return replacements


def update_booking(
    db: Session,
    *,
    booking: models.Booking,
    actor: models.User,
    mode: str,
    project_id: int,
    server_id: int | None,
    gpu_ids: list[int],
    start_at: datetime,
    end_at: datetime,
    description: str | None,
) -> models.Booking:
    existing_gpu_ids = {booking_gpu.gpu_id for booking_gpu in booking.gpus}
    gpus, server = validate_input(
        db,
        mode=mode,
        project_id=project_id,
        server_id=server_id,
        gpu_ids=gpu_ids,
        start_at=start_at,
        end_at=end_at,
        is_admin=actor.role == "admin",
        allowed_inactive_gpu_ids=existing_gpu_ids,
        allowed_inactive_project_id=booking.project_id,
        allowed_inactive_server_id=booking.server_id,
    )
    _lock_gpus(db, [gpu.id for gpu in gpus])

    conflict = _find_conflict(
        db,
        [gpu.id for gpu in gpus],
        start_at,
        end_at,
        mode,
        exclude_booking_ids={booking.id},
    )
    if conflict:
        db.rollback()
        raise HTTPException(status_code=409, detail=conflict)

    booking.mode = mode
    booking.project_id = project_id
    booking.server_id = server.id if server else None
    booking.start_at = start_at
    booking.end_at = end_at
    booking.description = description
    existing_gpu_links = {booking_gpu.gpu_id: booking_gpu for booking_gpu in booking.gpus}
    booking.gpus = [
        existing_gpu_links[gpu.id] if gpu.id in existing_gpu_links else models.BookingGpu(gpu_id=gpu.id)
        for gpu in gpus
    ]
    db.commit()
    db.refresh(booking)
    return booking
