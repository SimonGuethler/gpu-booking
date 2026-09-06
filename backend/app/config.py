from functools import lru_cache

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str = "sqlite:///./gpu_booking.db"
    jwt_secret: str = "dev-secret-change-me"
    jwt_algorithm: str = "HS256"
    jwt_expire_days: int = 90
    pbkdf2_iterations: int = Field(default=260_000, ge=1)
    auth_cookie_secure: bool = False
    max_booking_days: int = Field(default=7, ge=1)
    cors_origins: str = "http://localhost:5173,http://localhost:80"
    seed_admin_display_name: str = "Admin"
    seed_admin_password: str = ""
    seed_admin_email: str = "admin@example.local"

    @field_validator("cors_origins")
    @classmethod
    def reject_wildcard_origins(cls, value: str) -> str:
        if "*" in {origin.strip() for origin in value.split(",")}:
            raise ValueError(
                'CORS_ORIGINS: "*" ist nicht zulässig, da Session-Cookies per CORS mit '
                "Anmeldeinformationen gesendet werden (allow_credentials=True). Ein Wildcard-Origin "
                "würde jeden Ursprung erlauben. Konfiguriere stattdessen die konkreten Origins "
                "der Deployment-URLs, z. B. http://192.168.1.10:5173,http://192.168.1.10:80."
            )
        return value

    @property
    def cors_origin_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
