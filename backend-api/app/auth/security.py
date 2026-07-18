"""Security primitives: password hashing and JWT signing/verification.

Tokens: HS256. Access tokens are short-lived and stateless; they carry
the subject (username), the user id, role, and organization claims.
Refresh tokens are long-lived and stateful: every issued refresh jti is
persisted in ``RefreshTokenRepository`` so we can revoke, rotate, and
detect reuse.
"""

from __future__ import annotations

import logging
import uuid
from datetime import datetime, timedelta, timezone
from typing import NamedTuple, Optional

import bcrypt
import jwt

from app.auth.repositories import RefreshTokenRepository
from app.config import settings

logger = logging.getLogger(__name__)

ACCESS_TYPE = "access"
REFRESH_TYPE = "refresh"


class AccessToken(NamedTuple):
    token: str
    expires_in: int


class RefreshToken(NamedTuple):
    token: str
    expires_in: int
    jti: str


def hash_password(plain_password: str) -> str:
    """Hash a password using bcrypt and return the encoded hash as a string."""
    salt = bcrypt.gensalt()
    return bcrypt.hashpw(plain_password.encode("utf-8"), salt).decode("utf-8")


def verify_password(plain_password: str, password_hash: str) -> bool:
    """Constant-time verify of a password against a bcrypt hash.

    Returns False on any malformed hash. A malformed hash should never
    reach production, so we log loudly when one does instead of silently
    failing.
    """
    try:
        return bcrypt.checkpw(
            plain_password.encode("utf-8"),
            password_hash.encode("utf-8"),
        )
    except (ValueError, TypeError):
        logger.exception("verify_password received a malformed hash")
        return False


def _mint_jwt(payload: dict, lifetime: timedelta) -> str:
    now = datetime.now(tz=timezone.utc)
    payload = {
        **payload,
        "iat": int(now.timestamp()),
        "exp": int((now + lifetime).timestamp()),
    }
    return jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)


def create_access_token(
    *,
    user_id: str,
    username: str,
    role: str,
    organization_id: str,
) -> AccessToken:
    """Mint a short-lived access JWT carrying subject, uid, role, and org.

    Each access token carries a fresh ``jti`` so consecutive tokens minted
    in the same second are still observably distinguishable — useful for
    audit logging and a prerequisite for any future access-token
    blocklist.
    """
    expire_seconds = settings.jwt_expire_minutes * 60
    jti = str(uuid.uuid4())
    payload = {
        "sub": username,
        "uid": user_id,
        "role": role,
        "org": organization_id,
        "type": ACCESS_TYPE,
        "jti": jti,
    }
    return AccessToken(
        token=_mint_jwt(payload, timedelta(seconds=expire_seconds)),
        expires_in=expire_seconds,
    )


def create_refresh_token(*, user_id: str, username: str) -> RefreshToken:
    """Mint and persist a refresh JWT with a unique jti claim."""
    expire_seconds = settings.jwt_refresh_expire_days * 24 * 60 * 60
    jti = str(uuid.uuid4())
    payload = {"sub": username, "uid": user_id, "jti": jti, "type": REFRESH_TYPE}
    token = _mint_jwt(payload, timedelta(seconds=expire_seconds))
    now = datetime.now(tz=timezone.utc)
    RefreshTokenRepository.create(
        jti=jti,
        user_id=user_id,
        issued_at=now,
        expires_at=now + timedelta(seconds=expire_seconds),
    )
    return RefreshToken(token=token, expires_in=expire_seconds, jti=jti)


def _decode(token: str, expected_type: str) -> Optional[dict]:
    try:
        payload = jwt.decode(
            token,
            settings.jwt_secret,
            algorithms=[settings.jwt_algorithm],
        )
    except jwt.PyJWTError:
        return None
    if payload.get("type") != expected_type:
        return None
    return payload


def decode_access_token(token: str) -> Optional[dict]:
    """Decode + verify an access JWT. Returns the payload or None on any error."""
    return _decode(token, ACCESS_TYPE)


def decode_refresh_token(token: str) -> Optional[dict]:
    """Decode + verify a refresh JWT. Returns the payload or None on any error."""
    return _decode(token, REFRESH_TYPE)
