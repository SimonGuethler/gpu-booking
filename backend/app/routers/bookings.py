from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import or_, select
from sqlalchemy.orm import Session, selectinload

from app import services
from app.database import get_db
from app.deps import get_current_user
from app.models import Booking, BookingGpu, Gpu, Project, User
from app.schemas import (
    BookingCreate,
    BookingOut,
    BookingSeriesCreate,
    BookingSeriesUpdate,
    BookingUpdate,
)

router = APIRouter(prefix="/bookings", tags=["bookings"])


def _load_booking(db: Session, booking_id: int) -> Booking | None:
    return db.scalar(
        select(Booking)
        .options(
            selectinload(Booking.gpus).selectinload(BookingGpu.gpu),
            selectinload(Booking.user),
            selectinload(Booking.project).selectinload(Project.members),
        )
        .where(Booking.id == booking_id)
    )


def _load_series(db: Session, series_id: str) -> list[Booking]:
    return list(
        db.scalars(
            select(Booking)
            .options(
                selectinload(Booking.gpus).selectinload(BookingGpu.gpu),
                selectinload(Booking.user),
                selectinload(Booking.project).selectinload(Project.members),
            )
            .where(Booking.series_id == series_id)
            .order_by(Booking.start_at)
        ).all()
    )


def _to_out(booking: Booking) -> BookingOut:
    member_ids = sorted(m.user_id for m in booking.project.members)
    return BookingOut(
        id=booking.id,
        user=booking.user,
        project={"id": booking.project.id, "name": booking.project.name, "members": member_ids},
        gpus=[
            {
                "id": g.id,
                "server_id": g.server_id,
                "name": g.name,
                "memory_mb": g.memory_mb,
                "active": g.active,
            }
            for g in (bg.gpu for bg in booking.gpus)
        ],
        server_id=booking.server_id,
        mode=booking.mode,
        start_at=booking.start_at,
        end_at=booking.end_at,
        series_id=booking.series_id,
        series_start_at=booking.series_start_at,
        series_end_at=booking.series_end_at,
        daily_start_hour=booking.daily_start_hour,
        daily_end_hour=booking.daily_end_hour,
        description=booking.description,
    )


@router.get("", response_model=list[BookingOut])
def list_bookings(
    _from: datetime = Query(alias="from"),
    to: datetime = Query(),
    gpu_id: int | None = Query(default=None),
    user_id: int | None = Query(default=None),
    server_id: int | None = Query(default=None),
    project_id: int | None = Query(default=None),
    _: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[BookingOut]:
    if _from >= to:
        raise HTTPException(status_code=400, detail="Zeitraum ungültig: from muss vor to liegen.")

    stmt = (
        select(Booking)
        .options(
            selectinload(Booking.gpus).selectinload(BookingGpu.gpu),
            selectinload(Booking.user),
            selectinload(Booking.project).selectinload(Project.members),
        )
        .where(Booking.start_at < to, Booking.end_at > _from)
        .order_by(Booking.start_at)
    )
    if user_id is not None:
        stmt = stmt.where(Booking.user_id == user_id)
    if project_id is not None:
        stmt = stmt.where(Booking.project_id == project_id)
    if gpu_id is not None:
        gpu_bookings = select(BookingGpu.booking_id).where(BookingGpu.gpu_id == gpu_id)
        stmt = stmt.where(Booking.id.in_(gpu_bookings))
    if server_id is not None:
        server_gpu_bookings = (
            select(BookingGpu.booking_id)
            .join(Gpu, Gpu.id == BookingGpu.gpu_id)
            .where(Gpu.server_id == server_id)
        )
        stmt = stmt.where(or_(Booking.server_id == server_id, Booking.id.in_(server_gpu_bookings)))

    return [_to_out(b) for b in db.scalars(stmt).all()]


@router.post("", response_model=BookingOut, status_code=201)
def create_booking(
    body: BookingCreate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> BookingOut:
    booking = services.bookings.create_booking(
        db,
        user=user,
        mode=body.mode,
        project_id=body.project_id,
        server_id=body.server_id,
        gpu_ids=body.gpu_ids,
        start_at=body.start_at,
        end_at=body.end_at,
        description=body.description,
    )
    return _to_out(booking)


@router.post("/series", response_model=list[BookingOut], status_code=201)
def create_booking_series(
    body: BookingSeriesCreate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[BookingOut]:
    bookings = services.bookings.create_booking_series(
        db,
        user=user,
        mode=body.mode,
        project_id=body.project_id,
        server_id=body.server_id,
        gpu_ids=body.gpu_ids,
        intervals=[(interval.start_at, interval.end_at) for interval in body.intervals],
        series_start_at=body.series_start_at,
        series_end_at=body.series_end_at,
        daily_start_hour=body.daily_start_hour,
        daily_end_hour=body.daily_end_hour,
        description=body.description,
    )
    return [_to_out(booking) for booking in bookings]


@router.patch("/series/{series_id}", response_model=list[BookingOut])
def update_booking_series(
    series_id: str,
    body: BookingSeriesUpdate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[BookingOut]:
    bookings = _load_series(db, series_id)
    if not bookings:
        raise HTTPException(status_code=404, detail="Buchungsserie nicht gefunden.")
    if bookings[0].user_id != user.id and user.role != "admin":
        raise HTTPException(status_code=403, detail="Nur der Eigentümer oder Admin darf bearbeiten.")
    updated = services.bookings.update_booking_series(
        db,
        bookings=bookings,
        actor=user,
        mode=body.mode,
        project_id=body.project_id,
        server_id=body.server_id,
        gpu_ids=body.gpu_ids,
        intervals=[(interval.start_at, interval.end_at) for interval in body.intervals],
        series_start_at=body.series_start_at,
        series_end_at=body.series_end_at,
        daily_start_hour=body.daily_start_hour,
        daily_end_hour=body.daily_end_hour,
        description=body.description,
    )
    return [_to_out(booking) for booking in updated]


@router.delete("/series/{series_id}", status_code=204)
def delete_booking_series(
    series_id: str,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> None:
    bookings = _load_series(db, series_id)
    if not bookings:
        raise HTTPException(status_code=404, detail="Buchungsserie nicht gefunden.")
    if bookings[0].user_id != user.id and user.role != "admin":
        raise HTTPException(status_code=403, detail="Nur der Eigentümer oder Admin darf löschen.")
    for booking in bookings:
        db.delete(booking)
    db.commit()


@router.patch("/{booking_id}", response_model=BookingOut)
def update_booking(
    booking_id: int,
    body: BookingUpdate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> BookingOut:
    booking = _load_booking(db, booking_id)
    if booking is None:
        raise HTTPException(status_code=404, detail="Buchung nicht gefunden.")
    if booking.user_id != user.id and user.role != "admin":
        raise HTTPException(status_code=403, detail="Nur der Eigentümer oder Admin darf bearbeiten.")
    if booking.series_id is not None:
        raise HTTPException(
            status_code=409,
            detail="Diese Buchung gehört zu einer Serie und kann nur als Serie bearbeitet werden.",
        )

    booking = services.bookings.update_booking(
        db,
        booking=booking,
        actor=user,
        mode=body.mode,
        project_id=body.project_id,
        server_id=body.server_id,
        gpu_ids=body.gpu_ids,
        start_at=body.start_at,
        end_at=body.end_at,
        description=body.description,
    )
    return _to_out(booking)


@router.delete("/{booking_id}", status_code=204)
def delete_booking(
    booking_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> None:
    booking = db.get(Booking, booking_id)
    if booking is None:
        raise HTTPException(status_code=404, detail="Buchung nicht gefunden.")
    if booking.user_id != user.id and user.role != "admin":
        raise HTTPException(
            status_code=403,
            detail="Nur der Eigentümer oder Admin darf Buchungen löschen.",
        )
    if booking.series_id is not None:
        raise HTTPException(
            status_code=409,
            detail="Diese Buchung gehört zu einer Serie und kann nur als Serie gelöscht werden.",
        )
    db.delete(booking)
    db.commit()
