from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import DEFAULT_COLORS, User


def next_color(db: Session) -> str:
    """Wählt die erste ungenutzte Farbe aus der Palette zurück; sonst die erste."""
    used = set(db.scalars(select(User.color)).all())
    for color in DEFAULT_COLORS:
        if color not in used:
            return color
    return DEFAULT_COLORS[0]
