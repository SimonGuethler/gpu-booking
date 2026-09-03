from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.database import get_db
from app.deps import get_current_user, require_admin
from app.models import DEFAULT_COLORS, ROLE_ADMIN, Booking, Project, ProjectMember, User
from app.schemas import UserCreate, UserDirectoryOut, UserOut, UserUpdate, color_palette
from app.security import hash_password

router = APIRouter(prefix="/users", tags=["users"])

LAST_ADMIN_MESSAGE = (
    "Der letzte Administrator kann nicht deaktiviert, gesperrt, herabgestuft oder gelöscht werden."
)


def _next_color(db: Session) -> str:
    used = set(db.scalars(select(User.color)).all())
    for color in DEFAULT_COLORS:
        if color not in used:
            return color
    return DEFAULT_COLORS[0]


def _active_admin_ids(db: Session) -> list[int]:
    return list(
        db.scalars(
            select(User.id)
            .where(
                User.role == ROLE_ADMIN,
                User.approved.is_(True),
                User.active.is_(True),
            )
            .order_by(User.id)
            .with_for_update()
        ).all()
    )


@router.get("", response_model=list[UserOut])
def list_users(
    _: User = Depends(require_admin),
    db: Session = Depends(get_db),
) -> list[UserOut]:
    users = db.scalars(select(User).order_by(User.active.desc(), User.approved, User.display_name)).all()
    return [UserOut.model_validate(u) for u in users]


@router.get("/directory", response_model=list[UserDirectoryOut])
def user_directory(
    _: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[UserDirectoryOut]:
    users = db.scalars(
        select(User).where(User.approved.is_(True), User.active.is_(True)).order_by(User.display_name)
    ).all()
    return [UserDirectoryOut.model_validate(user) for user in users]


@router.get("/colors", response_model=list[str])
def palette(_: User = Depends(require_admin)) -> list[str]:
    return color_palette()


@router.post("", response_model=UserOut, status_code=201)
def create_user(
    body: UserCreate,
    _: User = Depends(require_admin),
    db: Session = Depends(get_db),
) -> UserOut:
    if db.scalar(select(User).where(User.display_name == body.display_name)):
        raise HTTPException(status_code=409, detail="Dieser Anzeigename ist bereits vergeben.")
    if db.scalar(select(User).where(User.email == body.email)):
        raise HTTPException(status_code=409, detail="Diese E-Mail-Adresse ist bereits vergeben.")

    user = User(
        display_name=body.display_name,
        email=body.email,
        password_hash=hash_password(body.password),
        role=body.role,
        approved=True,
        active=True,
        color=body.color or _next_color(db),
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return UserOut.model_validate(user)


@router.patch("/{user_id}", response_model=UserOut)
def update_user(
    user_id: int,
    body: UserUpdate,
    _: User = Depends(require_admin),
    db: Session = Depends(get_db),
) -> UserOut:
    user = db.get(User, user_id)
    if user is None:
        raise HTTPException(status_code=404, detail="Nutzer nicht gefunden.")

    if body.display_name is not None and body.display_name != user.display_name:
        if db.scalar(select(User).where(User.display_name == body.display_name, User.id != user_id)):
            raise HTTPException(status_code=409, detail="Dieser Anzeigename ist bereits vergeben.")
        user.display_name = body.display_name
    if body.email is not None and body.email != user.email:
        if db.scalar(select(User).where(User.email == body.email, User.id != user_id)):
            raise HTTPException(status_code=409, detail="Diese E-Mail-Adresse ist bereits vergeben.")
        user.email = body.email
    removes_active_admin = (
        user.role == ROLE_ADMIN
        and user.approved
        and user.active
        and (body.role not in (None, ROLE_ADMIN) or body.approved is False or body.active is False)
    )
    if removes_active_admin:
        if len(_active_admin_ids(db)) == 1:
            raise HTTPException(status_code=409, detail=LAST_ADMIN_MESSAGE)

    if body.role is not None:
        user.role = body.role
    if body.approved is not None:
        user.approved = body.approved
    if body.active is not None:
        user.active = body.active
    if body.color is not None:
        user.color = body.color
    if body.password is not None:
        user.password_hash = hash_password(body.password)

    db.commit()
    db.refresh(user)
    return UserOut.model_validate(user)


@router.delete("/{user_id}", status_code=204)
def delete_user(
    user_id: int,
    actor: User = Depends(require_admin),
    db: Session = Depends(get_db),
) -> None:
    user = db.get(User, user_id)
    if user is None:
        raise HTTPException(status_code=404, detail="Nutzer nicht gefunden.")
    if user.role == ROLE_ADMIN and user.approved and user.active and len(_active_admin_ids(db)) == 1:
        raise HTTPException(status_code=409, detail=LAST_ADMIN_MESSAGE)
    new_owner = actor
    if actor.id == user_id:
        replacement_id = next((admin_id for admin_id in _active_admin_ids(db) if admin_id != user_id), None)
        assert replacement_id is not None
        replacement = db.get(User, replacement_id)
        assert replacement is not None
        new_owner = replacement

    owned_projects = db.scalars(select(Project).where(Project.owner_id == user_id)).all()
    for project in owned_projects:
        project.owner_id = new_owner.id
        if (
            db.scalar(
                select(ProjectMember.id).where(
                    ProjectMember.project_id == project.id,
                    ProjectMember.user_id == new_owner.id,
                )
            )
            is None
        ):
            db.add(ProjectMember(project_id=project.id, user_id=new_owner.id))

    for booking in db.scalars(select(Booking).where(Booking.user_id == user_id)).all():
        db.delete(booking)

    db.execute(delete(ProjectMember).where(ProjectMember.user_id == user_id))
    db.delete(user)
    db.commit()
