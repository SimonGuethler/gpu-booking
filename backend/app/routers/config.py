from fastapi import APIRouter, Depends

from app.config import Settings, get_settings
from app.deps import get_current_user
from app.models import User
from app.schemas import AppConfigOut

router = APIRouter(prefix="/config", tags=["config"])


@router.get("", response_model=AppConfigOut)
def read_config(
    _user: User = Depends(get_current_user),
    settings: Settings = Depends(get_settings),
) -> AppConfigOut:
    return AppConfigOut(max_booking_days=settings.max_booking_days)
