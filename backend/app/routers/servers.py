from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.database import get_db
from app.deps import get_current_user, require_admin
from app.models import Booking, BookingGpu, Gpu, Server, User
from app.schemas import GpuCreate, GpuOut, GpuUpdate, ServerCreate, ServerOut, ServerUpdate

router = APIRouter(tags=["servers"])


@router.get("/servers", response_model=list[ServerOut])
def list_servers(_: User = Depends(get_current_user), db: Session = Depends(get_db)) -> list[ServerOut]:
    servers = db.scalars(select(Server).options(selectinload(Server.gpus)).order_by(Server.name)).all()
    return [ServerOut.model_validate(s) for s in servers]


@router.post("/servers", response_model=ServerOut, status_code=201)
def create_server(
    body: ServerCreate,
    _: User = Depends(require_admin),
    db: Session = Depends(get_db),
) -> ServerOut:
    if db.scalar(select(Server).where(Server.name == body.name)):
        raise HTTPException(status_code=409, detail="Ein Server mit diesem Namen existiert bereits.")
    server = Server(name=body.name, hostname=body.hostname)
    db.add(server)
    db.commit()
    db.refresh(server)
    return ServerOut.model_validate(server)


@router.patch("/servers/{server_id}", response_model=ServerOut)
def update_server(
    server_id: int,
    body: ServerUpdate,
    _: User = Depends(require_admin),
    db: Session = Depends(get_db),
) -> ServerOut:
    server = db.get(Server, server_id)
    if server is None:
        raise HTTPException(status_code=404, detail="Server nicht gefunden.")
    if (
        body.name is not None
        and body.name != server.name
        and db.scalar(select(Server).where(Server.name == body.name, Server.id != server_id))
    ):
        raise HTTPException(status_code=409, detail="Ein Server mit diesem Namen existiert bereits.")

    if body.name is not None:
        server.name = body.name
    if "hostname" in body.model_fields_set:
        server.hostname = body.hostname
    if body.active is not None:
        server.active = body.active

    db.commit()
    return ServerOut.model_validate(server)


@router.delete("/servers/{server_id}", status_code=204)
def delete_server(server_id: int, _: User = Depends(require_admin), db: Session = Depends(get_db)) -> None:
    server = db.get(Server, server_id)
    if server is None:
        raise HTTPException(status_code=404, detail="Server nicht gefunden.")

    gpu_ids = list(db.scalars(select(Gpu.id).where(Gpu.server_id == server_id)).all())
    used_ids = (
        set(db.scalars(select(BookingGpu.gpu_id).where(BookingGpu.gpu_id.in_(gpu_ids))).all())
        if gpu_ids
        else set()
    )
    has_cpu_bookings = (
        db.scalar(select(Booking.id).where(Booking.server_id == server_id).limit(1)) is not None
    )

    if not used_ids and not has_cpu_bookings:
        db.delete(server)
    else:
        for gpu in server.gpus:
            if gpu.id in used_ids:
                gpu.active = False
        server.active = False
    db.commit()


@router.post("/servers/{server_id}/gpus", response_model=GpuOut, status_code=201)
def create_gpu(
    server_id: int,
    body: GpuCreate,
    _: User = Depends(require_admin),
    db: Session = Depends(get_db),
) -> GpuOut:
    server = db.get(Server, server_id)
    if server is None:
        raise HTTPException(status_code=404, detail="Server nicht gefunden.")
    gpu = Gpu(server_id=server.id, name=body.name, memory_mb=body.memory_mb)
    db.add(gpu)
    db.commit()
    db.refresh(gpu)
    return GpuOut.model_validate(gpu)


@router.patch("/gpus/{gpu_id}", response_model=GpuOut)
def update_gpu(
    gpu_id: int,
    body: GpuUpdate,
    _: User = Depends(require_admin),
    db: Session = Depends(get_db),
) -> GpuOut:
    gpu = db.get(Gpu, gpu_id)
    if gpu is None:
        raise HTTPException(status_code=404, detail="GPU nicht gefunden.")
    if body.name is not None:
        gpu.name = body.name
    if "memory_mb" in body.model_fields_set:
        gpu.memory_mb = body.memory_mb
    if body.active is not None:
        gpu.active = body.active
    db.commit()
    db.refresh(gpu)
    return GpuOut.model_validate(gpu)


@router.delete("/gpus/{gpu_id}", status_code=204)
def delete_gpu(gpu_id: int, _: User = Depends(require_admin), db: Session = Depends(get_db)) -> None:
    gpu = db.get(Gpu, gpu_id)
    if gpu is None:
        raise HTTPException(status_code=404, detail="GPU nicht gefunden.")
    if db.scalar(select(BookingGpu.id).where(BookingGpu.gpu_id == gpu_id)) is not None:
        raise HTTPException(
            status_code=409,
            detail="Die GPU hat Buchungen und kann nicht gelöscht werden. Stattdessen deaktivieren.",
        )
    db.delete(gpu)
    db.commit()
