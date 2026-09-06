import hashlib
import hmac
import os
from datetime import UTC, datetime, timedelta

import jwt

from app.config import get_settings

AUTH_COOKIE_NAME = "gpu_booking_session"
CSRF_COOKIE_NAME = "gpu_booking_csrf"

# Format: "pbkdf2_sha256$<iterations>$<salt_hex>$<digest_hex>"; Legacy-Hashes
# ("salt_hex$digest_hex") stammen aus der ersten Version, die sämtliche Hashes
# mit 260 000 Iterationen erzeugte, und werden bei erfolgreicher Anmeldung
# migriert (needs_rehash/hash_password).
PASSWORD_ALGORITHM = "pbkdf2_sha256"

# Iterationszahl der ersten Release-Version. Sämtliche legacy-Hashes im
# 2-teiligen Format wurden damit erzeugt; sie verifizieren mit genau diesem
# Wert, unabhängig von der aktuell konfigurierten Zahl.
LEGACY_PBKDF2_ITERATIONS = 260_000


def hash_password(password: str) -> str:
    iterations = get_settings().pbkdf2_iterations
    salt = os.urandom(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, iterations)
    return f"{PASSWORD_ALGORITHM}${iterations}${salt.hex()}${digest.hex()}"


def needs_rehash(stored: str) -> bool:
    """True, wenn der Hash migriert werden sollte.

    Trifft auf legacy-Format zu und auf Hashes, deren Iterationszahl nicht der
    aktuell konfigurierten entspricht. Nach erfolgreichem Login ist der
    geprüfte Hash garantiert syntaktisch gültig; unbekannte Formate sollen
    daher ebenfalls ersetzt werden.
    """
    parts = stored.split("$")
    if len(parts) == 4 and parts[0] == PASSWORD_ALGORITHM:
        try:
            iterations = int(parts[1])
        except ValueError:
            return True
        return iterations != get_settings().pbkdf2_iterations
    return True


def verify_password(password: str, stored: str) -> bool:
    try:
        parts = stored.split("$")
        if len(parts) == 4 and parts[0] == PASSWORD_ALGORITHM:
            iterations = int(parts[1])
            salt_hex, digest_hex = parts[2], parts[3]
        elif len(parts) == 2:
            iterations = LEGACY_PBKDF2_ITERATIONS
            salt_hex, digest_hex = parts
        else:
            return False
        if not 1 <= iterations <= 2_147_483_647:
            # OpenSSL nimmt höchstens INT_MAX; größere Werte lieferten OverflowError.
            return False
        salt = bytes.fromhex(salt_hex)
        expected = bytes.fromhex(digest_hex)
    except ValueError:
        return False
    actual = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, iterations)
    return hmac.compare_digest(actual, expected)


# Unbekannte Konten durchlaufen denselben teuren Prüfpfad wie vorhandene Konten.
DUMMY_PASSWORD_HASH = hash_password("dummy-password-that-is-never-used")


def generate_csrf_token() -> str:
    return os.urandom(32).hex()


def verify_csrf_token(provided: str | None, expected: str | None) -> bool:
    if not provided or not expected:
        return False
    return hmac.compare_digest(provided, expected)


def create_access_token(user_id: int, password_changed_at: datetime | None) -> str:
    settings = get_settings()
    now = datetime.now(UTC)
    payload = {
        "sub": str(user_id),
        "iat": now,
        "exp": now + timedelta(days=settings.jwt_expire_days),
    }
    if password_changed_at is not None:
        # Stand des Passworts zum Ausstellungszeitpunkt (Epoch-Sekunden, µs-genau).
        # Ein späterer Passwortwechsel macht Tokens mit kleinerem Stand ungültig.
        payload["pwd"] = epoch_seconds(password_changed_at)
    return jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)


def epoch_seconds(value: datetime) -> float:
    """Epoch-Sekunden für naive-UTC-Zeitstempel (Konvention wie models.utcnow)."""
    return value.replace(tzinfo=UTC).timestamp()


def decode_access_token(token: str) -> tuple[int, float]:
    """Liefert (Nutzer-ID, Passwort-Stand zum Ausstellungszeitpunkt).

    Tokens ohne pwd-Claim (z. B. ausgestellt vor dem Upgrade) nutzen iat als
    Fallback: iat ist die auf ganze Sekunden abgerundete Ausstellungszeit und
    liegt damit garantiert unter jeder später gesetzten Änderungszeit.
    """
    settings = get_settings()
    payload = jwt.decode(token, settings.jwt_secret, algorithms=[settings.jwt_algorithm])
    password_state = payload.get("pwd")
    if password_state is None:
        password_state = payload.get("iat", 0)
    return int(payload["sub"]), float(password_state)
