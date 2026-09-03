from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import User
from app.security import AUTH_COOKIE_NAME, CSRF_COOKIE_NAME, decode_access_token, verify_csrf_token

bearer_scheme = HTTPBearer(auto_error=False)


def get_current_user(
    request: Request,
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    db: Session = Depends(get_db),
) -> User:
    token = credentials.credentials if credentials is not None else request.cookies.get(AUTH_COOKIE_NAME)
    if token is None:
        raise HTTPException(status_code=401, detail="Nicht angemeldet.")
    try:
        user_id = decode_access_token(token)
    except Exception:
        raise HTTPException(status_code=401, detail="Token ungültig oder abgelaufen.") from None
    user = db.get(User, user_id)
    if user is None:
        raise HTTPException(status_code=401, detail="Nutzer existiert nicht mehr.")
    if not user.active:
        raise HTTPException(status_code=401, detail="Dieses Konto wurde deaktiviert.")
    if not user.approved:
        raise HTTPException(status_code=401, detail="Dieses Konto ist nicht freigegeben.")
    if credentials is None and request.method not in {"GET", "HEAD", "OPTIONS"}:
        if not verify_csrf_token(
            request.headers.get("X-CSRF-Token"),
            request.cookies.get(CSRF_COOKIE_NAME),
        ):
            raise HTTPException(status_code=403, detail="CSRF-Prüfung fehlgeschlagen.")
    return user


def require_admin(user: User = Depends(get_current_user)) -> User:
    if user.role != "admin":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Nur Admins dürfen das.")
    return user
