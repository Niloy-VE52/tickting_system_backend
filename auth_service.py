import base64
import hashlib
import hmac
import json
import logging
import os
import time

from fastapi import HTTPException, Security
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

logger = logging.getLogger("auth_service")

security = HTTPBearer(auto_error=False)

AUTH_SECRET_KEY = os.getenv("AUTH_SECRET_KEY")
if not AUTH_SECRET_KEY:
    raise RuntimeError(
        "AUTH_SECRET_KEY is not set. Generate one with: "
        "python -c \"import secrets; print(secrets.token_hex(32))\""
    )

if os.getenv("ADMIN_PASSWORD", "admin123") == "admin123":
    logger.warning("⚠️  Using default admin password — do not deploy this to production.")

DEFAULT_USERS = {
    os.getenv("ADMIN_USERNAME", "admin"): {
        "password": os.getenv("ADMIN_PASSWORD", "admin123"),
        "name": "Sarah Jenkins",
        "email": "sarah.jenkins@grandview-residences.com",
        "role": "Property Director",
        "avatar": "SJ",
    },
    "manager": {
        "password": "manager123",
        "name": "Alex Mercer",
        "email": "alex.mercer@grandview-residences.com",
        "role": "Property Manager",
        "avatar": "AM",
    },
    "tech": {
        "password": "tech123",
        "name": "Dave Rodriguez",
        "email": "dave.rodriguez@grandview-residences.com",
        "role": "Maintenance Lead",
        "avatar": "DR",
    },
}


def generate_token(username: str, expires_in: int = 86400 * 7) -> str:
    payload = {
        "sub": username,
        "exp": int(time.time()) + expires_in,
    }
    payload_b64 = base64.urlsafe_b64encode(json.dumps(payload).encode()).decode()
    signature = hmac.new(AUTH_SECRET_KEY.encode(), payload_b64.encode(), hashlib.sha256).hexdigest()
    return f"{payload_b64}.{signature}"


def decode_token(token: str):
    try:
        parts = token.split(".")
        if len(parts) != 2:
            return None
        payload_b64, signature = parts
        expected_sig = hmac.new(AUTH_SECRET_KEY.encode(), payload_b64.encode(), hashlib.sha256).hexdigest()
        if not hmac.compare_digest(signature, expected_sig):
            return None
        payload = json.loads(base64.urlsafe_b64decode(payload_b64.encode()).decode())
        if payload.get("exp", 0) < time.time():
            return None
        return payload
    except Exception:
        return None


def get_current_user(credentials: HTTPAuthorizationCredentials = Security(security)):
    if not credentials or not credentials.credentials:
        raise HTTPException(status_code=401, detail="Missing or invalid authentication credentials")
    payload = decode_token(credentials.credentials)
    if not payload:
        raise HTTPException(status_code=401, detail="Session expired or invalid")
    username = payload.get("sub")
    user = DEFAULT_USERS.get(username)
    if not user:
        raise HTTPException(status_code=401, detail="User not found")
    return {
        "username": username,
        "name": user["name"],
        "email": user["email"],
        "role": user["role"],
        "avatar": user["avatar"],
    }
