import secrets
import os
from datetime import datetime, timezone, timedelta
from typing import Optional

ADMIN_SESSION_DURATION = timedelta(hours=4)

admin_sessions = {}


def generate_admin_token() -> str:
    return secrets.token_urlsafe(32)


def verify_admin_password(password: str) -> bool:
    expected = os.environ.get("ADMIN_CSV_PASSWORD")
    if not expected:
        print("⚠️ ADMIN_CSV_PASSWORD not configured", flush=True)
        return False
    return password == expected


def verify_csv_password(password: str) -> bool:
    return verify_admin_password(password)


def create_admin_session() -> str:
    token = generate_admin_token()
    now = datetime.now(timezone.utc)
    admin_sessions[token] = {
        "created_at": now,
        "expires_at": now + ADMIN_SESSION_DURATION,
        "type": "admin"
    }
    cleanup_expired_sessions()
    return token


def verify_admin_token(token: Optional[str]) -> bool:
    if not token or token not in admin_sessions:
        return False
    session = admin_sessions[token]
    now = datetime.now(timezone.utc)
    if now > session["expires_at"]:
        del admin_sessions[token]
        return False
    return session["type"] == "admin"


def cleanup_expired_sessions():
    now = datetime.now(timezone.utc)
    expired = [t for t, s in admin_sessions.items() if now > s["expires_at"]]
    for t in expired:
        del admin_sessions[t]


def revoke_admin_session(token: str):
    if token in admin_sessions:
        del admin_sessions[token]


def is_admin_route(path: str) -> bool:
    admin_prefixes = ["/admin", "/api/config/"]
    return any(path.startswith(prefix) for prefix in admin_prefixes)
