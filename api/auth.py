"""
Prosta autoryzacja admina — hash SHA-256 hasła w settings.
Cookie httponly z tokenem sesji.
"""
import hashlib
import secrets
from .database import get_conn

SALT = "antyramy_kalk_2026"
COOKIE_NAME = "kalk_admin"


def hash_password(password: str) -> str:
    return hashlib.sha256(f"{password}{SALT}".encode()).hexdigest()


def verify_password(password: str) -> bool:
    with get_conn() as conn:
        row = conn.execute(
            "SELECT value FROM settings WHERE key = 'admin_password_hash'"
        ).fetchone()
    stored = row["value"] if row else ""
    if not stored:
        return False
    return secrets.compare_digest(stored, hash_password(password))


def set_password(new_password: str) -> None:
    with get_conn() as conn:
        conn.execute(
            "UPDATE settings SET value = ? WHERE key = 'admin_password_hash'",
            (hash_password(new_password),),
        )


def make_session_token(password: str) -> str:
    return hashlib.sha256(f"{hash_password(password)}_session_{SALT}".encode()).hexdigest()


def verify_cookie(token: str) -> bool:
    with get_conn() as conn:
        row = conn.execute(
            "SELECT value FROM settings WHERE key = 'admin_password_hash'"
        ).fetchone()
    stored = row["value"] if row else ""
    if not stored:
        return False
    expected = hashlib.sha256(f"{stored}_session_{SALT}".encode()).hexdigest()
    return secrets.compare_digest(token, expected)
