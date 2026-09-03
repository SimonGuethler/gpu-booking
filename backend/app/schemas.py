from datetime import UTC, datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.models import DEFAULT_COLORS, MODES, ROLES

HOUR_GRID_MSG = "Zeiten müssen auf vollen Stunden liegen (Minute und Sekunde 00)."
MIN_DURATION_MSG = "Mindestdauer einer Buchung ist 1 Stunde."


def _to_naive_utc(value: datetime) -> datetime:
    if value.tzinfo is not None:
        return value.astimezone(UTC).replace(tzinfo=None)
    return value


def _normalize_email(value: str) -> str:
    normalized = value.strip().lower()
    local, separator, domain = normalized.partition("@")
    if not separator or not local or not domain or any(char.isspace() for char in normalized):
        raise ValueError("Bitte eine gültige E-Mail-Adresse eingeben.")
    return normalized


def _validate_hour_grid(start_at: datetime, end_at: datetime) -> None:
    if start_at.minute != 0 or start_at.second != 0 or start_at.microsecond != 0:
        raise ValueError(HOUR_GRID_MSG)
    if end_at.minute != 0 or end_at.second != 0 or end_at.microsecond != 0:
        raise ValueError(HOUR_GRID_MSG)


def _reject_explicit_null(model: BaseModel, fields: set[str]) -> None:
    for field_name in fields & model.model_fields_set:
        if getattr(model, field_name) is None:
            raise ValueError(f"{field_name} darf nicht null sein.")


class BookingInput(BaseModel):
    gpu_ids: list[int] = Field(default_factory=list)
    server_id: int | None = None
    mode: str
    project_id: int
    start_at: datetime
    end_at: datetime
    description: str | None = Field(default=None, max_length=2000)

    @field_validator("start_at", "end_at")
    @classmethod
    def _naive_utc(cls, value: datetime) -> datetime:
        return _to_naive_utc(value)

    @field_validator("mode")
    @classmethod
    def _mode(cls, value: str) -> str:
        if value not in MODES:
            raise ValueError(f"mode muss eine von {', '.join(MODES)} sein.")
        return value

    @model_validator(mode="after")
    def _validate_times(self) -> "BookingInput":
        start_at, end_at = self.start_at, self.end_at
        if start_at >= end_at:
            raise ValueError("start_at muss vor end_at liegen.")
        _validate_hour_grid(start_at, end_at)
        duration = (end_at - start_at).total_seconds() / 3600
        if duration < 1:
            raise ValueError(MIN_DURATION_MSG)
        if self.mode == "cpu":
            if self.gpu_ids:
                raise ValueError("cpu-Buchungen dürfen keine GPUs belegen.")
            if self.server_id is None:
                raise ValueError("Bitte einen Server für die CPU-Buchung wählen.")
        elif not self.gpu_ids:
            raise ValueError("Bitte mindestens eine GPU wählen (train/dev).")
        elif self.server_id is not None:
            raise ValueError("server_id darf nur für CPU-Buchungen gesetzt werden.")
        return self


class BookingCreate(BookingInput):
    pass


class BookingUpdate(BookingInput):
    pass


class BookingInterval(BaseModel):
    start_at: datetime
    end_at: datetime

    @field_validator("start_at", "end_at")
    @classmethod
    def _naive_utc(cls, value: datetime) -> datetime:
        return _to_naive_utc(value)

    @model_validator(mode="after")
    def _validate_times(self) -> "BookingInterval":
        if self.start_at >= self.end_at:
            raise ValueError("start_at muss vor end_at liegen.")
        _validate_hour_grid(self.start_at, self.end_at)
        if (self.end_at - self.start_at).total_seconds() < 3600:
            raise ValueError(MIN_DURATION_MSG)
        return self


class BookingSeriesCreate(BaseModel):
    gpu_ids: list[int] = Field(default_factory=list)
    server_id: int | None = None
    mode: str
    project_id: int
    intervals: list[BookingInterval] = Field(min_length=1, max_length=366)
    series_start_at: datetime
    series_end_at: datetime
    daily_start_hour: int = Field(ge=0, le=23)
    daily_end_hour: int = Field(ge=1, le=23)
    description: str | None = Field(default=None, max_length=2000)

    @field_validator("series_start_at", "series_end_at")
    @classmethod
    def _naive_utc(cls, value: datetime) -> datetime:
        return _to_naive_utc(value)

    @field_validator("mode")
    @classmethod
    def _mode(cls, value: str) -> str:
        if value not in MODES:
            raise ValueError(f"mode muss eine von {', '.join(MODES)} sein.")
        return value

    @model_validator(mode="after")
    def _validate_resources_and_intervals(self) -> "BookingSeriesCreate":
        if self.mode == "cpu":
            if self.gpu_ids:
                raise ValueError("cpu-Buchungen dürfen keine GPUs belegen.")
            if self.server_id is None:
                raise ValueError("Bitte einen Server für die CPU-Buchung wählen.")
        elif not self.gpu_ids:
            raise ValueError("Bitte mindestens eine GPU wählen (train/dev).")
        elif self.server_id is not None:
            raise ValueError("server_id darf nur für CPU-Buchungen gesetzt werden.")

        if self.series_start_at >= self.series_end_at:
            raise ValueError("series_start_at muss vor series_end_at liegen.")
        _validate_hour_grid(self.series_start_at, self.series_end_at)
        if self.daily_start_hour >= self.daily_end_hour:
            raise ValueError("daily_start_hour muss vor daily_end_hour liegen.")

        ordered = sorted(self.intervals, key=lambda interval: interval.start_at)
        if ordered != self.intervals:
            raise ValueError("intervals müssen chronologisch sortiert sein.")
        for previous, current in zip(ordered, ordered[1:], strict=False):
            if previous.end_at > current.start_at:
                raise ValueError("intervals dürfen sich nicht überschneiden.")
        if ordered[0].start_at < self.series_start_at or ordered[-1].end_at > self.series_end_at:
            raise ValueError("intervals müssen innerhalb des Serienzeitraums liegen.")
        return self


class BookingSeriesUpdate(BookingSeriesCreate):
    pass


class BookingOutUser(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    display_name: str
    color: str
    role: str


class BookingOutProject(BaseModel):
    id: int
    name: str
    members: list[int]


class BookingOut(BaseModel):
    id: int
    user: BookingOutUser
    project: BookingOutProject
    gpus: list["GpuOut"]
    server_id: int | None
    mode: str
    start_at: datetime
    end_at: datetime
    series_id: str | None
    series_start_at: datetime | None
    series_end_at: datetime | None
    daily_start_hour: int | None
    daily_end_hour: int | None
    description: str | None

    @field_validator("start_at", "end_at", "series_start_at", "series_end_at")
    @classmethod
    def _naive_utc(cls, value: datetime | None) -> datetime | None:
        return _to_naive_utc(value) if value is not None else None


class UserCreate(BaseModel):
    display_name: str = Field(min_length=2, max_length=80)
    email: str = Field(max_length=255)
    password: str = Field(min_length=8, max_length=200)
    role: str = Field(default="user")
    color: str | None = Field(default=None, pattern=r"^#[0-9a-fA-F]{6}$")

    @field_validator("role")
    @classmethod
    def _role(cls, value: str) -> str:
        if value not in ROLES:
            raise ValueError(f"Rolle muss eine von {', '.join(ROLES)} sein.")
        return value

    @field_validator("email")
    @classmethod
    def _email_lower(cls, value: str) -> str:
        return _normalize_email(value)

    @field_validator("display_name")
    @classmethod
    def _display_name_trim(cls, value: str) -> str:
        value = value.strip()
        if len(value) < 2:
            raise ValueError("Der Anzeigename muss mindestens 2 Zeichen lang sein.")
        return value


def _validate_strong_password(value: str) -> str:
    if not any(character.isupper() for character in value):
        raise ValueError("Das Passwort muss mindestens einen Großbuchstaben enthalten.")
    if not any(character.islower() for character in value):
        raise ValueError("Das Passwort muss mindestens einen Kleinbuchstaben enthalten.")
    if not any(character.isdigit() for character in value):
        raise ValueError("Das Passwort muss mindestens eine Zahl enthalten.")
    return value


class RegistrationCreate(BaseModel):
    display_name: str = Field(min_length=2, max_length=80)
    email: str = Field(max_length=255)
    password: str = Field(min_length=8, max_length=200)
    password_confirmation: str = Field(min_length=8, max_length=200)

    @field_validator("display_name")
    @classmethod
    def _display_name_trim(cls, value: str) -> str:
        value = value.strip()
        if len(value) < 2:
            raise ValueError("Der Anzeigename muss mindestens 2 Zeichen lang sein.")
        return value

    @field_validator("email")
    @classmethod
    def _email_lower(cls, value: str) -> str:
        return _normalize_email(value)

    @field_validator("password")
    @classmethod
    def _strong_password(cls, value: str) -> str:
        return _validate_strong_password(value)

    @model_validator(mode="after")
    def _passwords_match(self) -> "RegistrationCreate":
        if self.password != self.password_confirmation:
            raise ValueError("Die Passwörter stimmen nicht überein.")
        return self


class RegistrationResponse(BaseModel):
    message: str


class UserUpdate(BaseModel):
    display_name: str | None = Field(default=None, min_length=2, max_length=80)
    email: str | None = Field(default=None, max_length=255)
    role: str | None = None
    color: str | None = Field(default=None, pattern=r"^#[0-9a-fA-F]{6}$")
    password: str | None = Field(default=None, min_length=8, max_length=200)
    approved: bool | None = None
    active: bool | None = None

    @field_validator("display_name")
    @classmethod
    def _display_name_trim(cls, value: str | None) -> str | None:
        if value is None:
            return None
        value = value.strip()
        if len(value) < 2:
            raise ValueError("Der Anzeigename muss mindestens 2 Zeichen lang sein.")
        return value

    @field_validator("email")
    @classmethod
    def _email_lower(cls, value: str | None) -> str | None:
        return _normalize_email(value) if value is not None else value

    @field_validator("role")
    @classmethod
    def _role(cls, value: str | None) -> str | None:
        if value is not None and value not in ROLES:
            raise ValueError(f"Rolle muss eine von {', '.join(ROLES)} sein.")
        return value

    @model_validator(mode="after")
    def _required_fields_are_not_null(self) -> "UserUpdate":
        _reject_explicit_null(
            self,
            {"display_name", "email", "role", "color", "password", "approved", "active"},
        )
        return self


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    display_name: str
    email: str
    role: str
    approved: bool
    active: bool
    color: str
    created_at: datetime


class UserDirectoryOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    display_name: str
    color: str


class ServerCreate(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    hostname: str | None = Field(default=None, max_length=255)

    @field_validator("name")
    @classmethod
    def _trim(cls, value: str) -> str:
        return value.strip()


class ServerUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=120)
    hostname: str | None = Field(default=None, max_length=255)
    active: bool | None = None

    @field_validator("name")
    @classmethod
    def _trim(cls, value: str | None) -> str | None:
        return value.strip() if value is not None else value

    @model_validator(mode="after")
    def _required_fields_are_not_null(self) -> "ServerUpdate":
        _reject_explicit_null(self, {"name", "active"})
        return self


class GpuCreate(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    memory_mb: int | None = Field(default=None, ge=0, le=2**31)

    @field_validator("name")
    @classmethod
    def _trim(cls, value: str) -> str:
        return value.strip()


class GpuUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=120)
    memory_mb: int | None = Field(default=None, ge=0, le=2**31)
    active: bool | None = None

    @field_validator("name")
    @classmethod
    def _trim(cls, value: str | None) -> str | None:
        return value.strip() if value is not None else value

    @model_validator(mode="after")
    def _required_fields_are_not_null(self) -> "GpuUpdate":
        _reject_explicit_null(self, {"name", "active"})
        return self


class GpuOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    server_id: int
    name: str
    memory_mb: int | None
    active: bool


class ServerOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    hostname: str | None
    active: bool
    gpus: list[GpuOut] = Field(default_factory=list)


class ProjectCreate(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    description: str | None = Field(default=None, max_length=2000)
    member_ids: list[int] = Field(default_factory=list)

    @field_validator("name")
    @classmethod
    def _trim(cls, value: str) -> str:
        return value.strip()


class ProjectUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=120)
    description: str | None = Field(default=None, max_length=2000)
    active: bool | None = None
    member_ids: list[int] | None = None

    @field_validator("name")
    @classmethod
    def _trim(cls, value: str | None) -> str | None:
        return value.strip() if value is not None else value

    @model_validator(mode="after")
    def _required_fields_are_not_null(self) -> "ProjectUpdate":
        _reject_explicit_null(self, {"name", "active", "member_ids"})
        return self


class ProjectMemberOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    display_name: str
    color: str


class ProjectOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    description: str | None
    owner_id: int
    active: bool
    members: list[ProjectMemberOut] = Field(default_factory=list)
    created_at: datetime


class LoginRequest(BaseModel):
    email: str
    password: str = Field(max_length=200)

    @field_validator("email")
    @classmethod
    def _email_lower(cls, value: str) -> str:
        return _normalize_email(value)


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserOut


BookingOut.model_rebuild()


def color_palette() -> list[str]:
    return list(DEFAULT_COLORS)


class AppConfigOut(BaseModel):
    max_booking_days: int
