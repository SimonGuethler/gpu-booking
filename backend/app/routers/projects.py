from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.database import get_db
from app.deps import get_current_user
from app.models import Booking, Project, ProjectMember, User
from app.schemas import ProjectCreate, ProjectMemberOut, ProjectOut, ProjectUpdate

router = APIRouter(prefix="/projects", tags=["projects"])


def _load_project(db: Session, project_id: int) -> Project | None:
    return db.scalar(
        select(Project)
        .options(selectinload(Project.members).selectinload(ProjectMember.user))
        .where(Project.id == project_id)
    )


def _to_out(project: Project) -> ProjectOut:
    return ProjectOut(
        id=project.id,
        name=project.name,
        description=project.description,
        owner_id=project.owner_id,
        active=project.active,
        created_at=project.created_at,
        members=[
            ProjectMemberOut(id=m.user_id, display_name=m.user.display_name, color=m.user.color)
            for m in project.members
        ],
    )


def _can_manage(project: Project, user: User) -> bool:
    return user.role == "admin" or project.owner_id == user.id


def _set_members(db: Session, project: Project, member_ids: list[int]) -> None:
    ids = set(member_ids) | {project.owner_id}
    db.flush()
    current = {
        m.user_id
        for m in db.scalars(select(ProjectMember).where(ProjectMember.project_id == project.id)).all()
    }
    for user_id in current - ids:
        member = db.scalar(
            select(ProjectMember).where(
                ProjectMember.project_id == project.id, ProjectMember.user_id == user_id
            )
        )
        if member is not None:
            db.delete(member)
    for user_id in ids - current:
        if db.get(User, user_id) is not None:
            db.add(ProjectMember(project_id=project.id, user_id=user_id))


@router.get("", response_model=list[ProjectOut])
def list_projects(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[ProjectOut]:
    stmt = (
        select(Project)
        .options(selectinload(Project.members).selectinload(ProjectMember.user))
        .order_by(Project.name)
    )
    if user.role != "admin":
        stmt = stmt.where(Project.active.is_(True))
    return [_to_out(p) for p in db.scalars(stmt).all()]


@router.post("", response_model=ProjectOut, status_code=201)
def create_project(
    body: ProjectCreate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ProjectOut:
    if db.scalar(select(Project).where(Project.name == body.name)):
        raise HTTPException(status_code=409, detail="Ein Projekt mit diesem Namen existiert bereits.")

    project = Project(
        name=body.name,
        description=body.description,
        owner_id=user.id,
    )
    db.add(project)
    db.flush()
    db.add(ProjectMember(project_id=project.id, user_id=user.id))
    _set_members(db, project, body.member_ids)
    db.commit()
    db.expire_all()
    result = _load_project(db, project.id)
    assert result is not None
    return _to_out(result)


@router.patch("/{project_id}", response_model=ProjectOut)
def update_project(
    project_id: int,
    body: ProjectUpdate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ProjectOut:
    project = _load_project(db, project_id)
    if project is None:
        raise HTTPException(status_code=404, detail="Projekt nicht gefunden.")
    if not _can_manage(project, user):
        raise HTTPException(status_code=403, detail="Nur Owner oder Admin dürfen das Projekt bearbeiten.")
    if (
        body.name is not None
        and body.name != project.name
        and db.scalar(select(Project).where(Project.name == body.name, Project.id != project_id))
    ):
        raise HTTPException(status_code=409, detail="Ein Projekt mit diesem Namen existiert bereits.")

    if body.name is not None:
        project.name = body.name
    if "description" in body.model_fields_set:
        project.description = body.description
    if body.active is not None:
        project.active = body.active
    if body.member_ids is not None:
        _set_members(db, project, body.member_ids)

    db.commit()
    db.expire_all()
    result = _load_project(db, project.id)
    assert result is not None
    return _to_out(result)


@router.delete("/{project_id}", status_code=204)
def delete_project(
    project_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> None:
    project = _load_project(db, project_id)
    if project is None:
        raise HTTPException(status_code=404, detail="Projekt nicht gefunden.")
    if not _can_manage(project, user):
        raise HTTPException(status_code=403, detail="Nur Owner oder Admin dürfen das Projekt löschen.")
    for booking in db.scalars(select(Booking).where(Booking.project_id == project_id)).all():
        db.delete(booking)
    db.delete(project)
    db.commit()
