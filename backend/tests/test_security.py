import hashlib
import os
from types import SimpleNamespace

from app.config import get_settings
from app.security import (
    LEGACY_PBKDF2_ITERATIONS,
    PASSWORD_ALGORITHM,
    hash_password,
    needs_rehash,
    verify_password,
)


def test_hash_password_roundtrip():
    stored = hash_password("s3cret-password")

    assert verify_password("s3cret-password", stored)
    assert not verify_password("wrong-password", stored)


def test_hash_password_records_iterations():
    stored = hash_password("s3cret-password")
    algorithm, iterations, _salt, _digest = stored.split("$")

    assert algorithm == PASSWORD_ALGORITHM
    assert int(iterations) == get_settings().pbkdf2_iterations


def test_verify_password_rejects_malformed_hashes():
    assert not verify_password("pw", "not-a-hash")
    assert not verify_password("pw", "a$b$c")
    assert not verify_password("pw", f"{PASSWORD_ALGORITHM}$0$00$ab")
    assert not verify_password("pw", f"{PASSWORD_ALGORITHM}$1000$zz$ab")
    assert not verify_password("pw", "unknown_algo$1000$00$ab")


def test_verify_password_rejects_oversized_iteration_count():
    # Syntaktisch gültig, sprengt aber OpenSSL-INT_MAX – False statt Exception.
    assert not verify_password("pw", f"{PASSWORD_ALGORITHM}$1000000000000$00$ab")


def test_verify_password_uses_iterations_recorded_in_hash(monkeypatch):
    stored = hash_password("s3cret-password")

    monkeypatch.setattr(
        "app.security.get_settings",
        lambda: SimpleNamespace(pbkdf2_iterations=12_345),
    )

    # Der im Hash hinterlegte Wert zählt – die aktuelle Einstellung ist egal.
    assert verify_password("s3cret-password", stored)
    assert not verify_password("wrong-password", stored)


def test_needs_rehash_accepts_current_format():
    assert not needs_rehash(hash_password("s3cret-password"))


def test_needs_rehash_flags_legacy_format():
    salt = os.urandom(16)
    expected = hashlib.pbkdf2_hmac("sha256", b"s3cret-password", salt, get_settings().pbkdf2_iterations)
    assert needs_rehash(f"{salt.hex()}${expected.hex()}")


def test_needs_rehash_flags_outdated_iteration_count():
    salt = os.urandom(16)
    digest = hashlib.pbkdf2_hmac("sha256", b"s3cret-password", salt, 123).hex()
    stale = f"{PASSWORD_ALGORITHM}$123${salt.hex()}${digest}"

    assert not needs_rehash(f"{PASSWORD_ALGORITHM}${get_settings().pbkdf2_iterations}${salt.hex()}${digest}")
    assert needs_rehash(stale)


def test_needs_rehash_flags_malformed_hashes():
    assert needs_rehash("not-a-hash")
    assert needs_rehash(f"{PASSWORD_ALGORITHM}$zz$00$ab")
    assert needs_rehash("")


def test_verify_password_accepts_legacy_format(monkeypatch):
    salt = os.urandom(16)
    expected = hashlib.pbkdf2_hmac("sha256", b"s3cret-password", salt, LEGACY_PBKDF2_ITERATIONS)
    legacy = f"{salt.hex()}${expected.hex()}"

    monkeypatch.setattr(
        "app.security.get_settings",
        lambda: SimpleNamespace(pbkdf2_iterations=LEGACY_PBKDF2_ITERATIONS * 2),
    )

    # Legacy-Hashes wurden von der ersten Version immer mit 260 000 Iterationen
    # erzeugt und verifizieren unabhängig von der aktuellen Einstellung.
    assert verify_password("s3cret-password", legacy)
    assert not verify_password("wrong-password", legacy)
