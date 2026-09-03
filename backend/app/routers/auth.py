from fastapi import APIRouter, Depends, HTTPException, Request, Response
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.config import get_settings
from app.database import get_db
from app.deps import get_current_user
from app.models import DEFAULT_COLORS, User
from app.schemas import (
    LoginRequest,
    RegistrationCreate,
    RegistrationResponse,
    TokenResponse,
    UserOut,
)
from app.security import (
    AUTH_COOKIE_NAME,
    CSRF_COOKIE_NAME,
    DUMMY_PASSWORD_HASH,
    create_access_token,
    generate_csrf_token,
    hash_password,
    verify_csrf_token,
    verify_password,
)

router = APIRouter(prefix="/auth", tags=["auth"])


def _next_color(db: Session) -> str:
    used = set(db.scalars(select(User.color)).all())
    return next((color for color in DEFAULT_COLORS if color not in used), DEFAULT_COLORS[0])


def _set_cookie(response: Response, name: str, value: str, *, httponly: bool) -> None:
    settings = get_settings()
    response.set_cookie(
        key=name,
        value=value,
        max_age=settings.jwt_expire_days * 86_400,
        httponly=httponly,
        secure=settings.auth_cookie_secure,
        samesite="strict",
        path="/",
    )


def _clear_cookie(response: Response, name: str, *, httponly: bool) -> None:
    settings = get_settings()
    response.delete_cookie(
        key=name,
        httponly=httponly,
        secure=settings.auth_cookie_secure,
        samesite="strict",
        path="/",
    )


@router.post("/login", response_model=TokenResponse)
def login(body: LoginRequest, response: Response, db: Session = Depends(get_db)) -> TokenResponse:
    user = db.scalar(select(User).where(func.lower(User.email) == body.email))
    password_hash = user.password_hash if user is not None else DUMMY_PASSWORD_HASH
    password_valid = verify_password(body.password, password_hash)
    if user is None or not password_valid:
        raise HTTPException(status_code=401, detail="E-Mail-Adresse oder Passwort falsch.")
    if not user.active:
        raise HTTPException(status_code=403, detail="Dieses Konto wurde deaktiviert.")
    if not user.approved:
        raise HTTPException(
            status_code=403,
            detail="Dein Konto wartet noch auf die Freigabe durch einen Administrator.",
        )
    csrf_token = generate_csrf_token()
    access_token = create_access_token(user.id)
    _set_cookie(response, AUTH_COOKIE_NAME, access_token, httponly=True)
    _set_cookie(response, CSRF_COOKIE_NAME, csrf_token, httponly=False)
    response.headers["X-CSRF-Token"] = csrf_token
    response.headers["Cache-Control"] = "no-store"
    return TokenResponse(access_token=access_token, user=UserOut.model_validate(user))


@router.post("/register", response_model=RegistrationResponse, status_code=201)
def register(body: RegistrationCreate, db: Session = Depends(get_db)) -> RegistrationResponse:
    if db.scalar(select(User).where(User.display_name == body.display_name)):
        raise HTTPException(status_code=409, detail="Dieser Anzeigename ist bereits vergeben.")
    if db.scalar(select(User).where(func.lower(User.email) == body.email)):
        raise HTTPException(status_code=409, detail="Diese E-Mail-Adresse ist bereits vergeben.")

    db.add(
        User(
            display_name=body.display_name,
            email=body.email,
            password_hash=hash_password(body.password),
            role="user",
            approved=False,
            active=True,
            color=_next_color(db),
        )
    )
    db.commit()
    return RegistrationResponse(
        message="Registrierung erfolgreich. Dein Konto wartet auf die Freigabe durch einen Administrator."
    )


@router.get("/me", response_model=UserOut)
def me(
    request: Request,
    response: Response,
    user: User = Depends(get_current_user),
) -> UserOut:
    csrf_token = request.cookies.get(CSRF_COOKIE_NAME) or generate_csrf_token()
    if request.cookies.get(CSRF_COOKIE_NAME) is None:
        _set_cookie(response, CSRF_COOKIE_NAME, csrf_token, httponly=False)
    response.headers["X-CSRF-Token"] = csrf_token
    response.headers["Cache-Control"] = "no-store"
    return UserOut.model_validate(user)


@router.post("/logout", status_code=204)
def logout(request: Request, response: Response) -> None:
    if request.cookies.get(AUTH_COOKIE_NAME) is not None and not verify_csrf_token(
        request.headers.get("X-CSRF-Token"),
        request.cookies.get(CSRF_COOKIE_NAME),
    ):
        raise HTTPException(status_code=403, detail="CSRF-Prüfung fehlgeschlagen.")
    _clear_cookie(response, AUTH_COOKIE_NAME, httponly=True)
    _clear_cookie(response, CSRF_COOKIE_NAME, httponly=False)
    response.headers["Cache-Control"] = "no-store"
