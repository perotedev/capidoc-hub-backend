import uuid
from datetime import datetime, timedelta, timezone
from enum import StrEnum
from typing import Any

import jwt
from passlib.context import CryptContext

from app.core.config import get_settings

settings = get_settings()

_password_context = CryptContext(schemes=["argon2"], deprecated="auto")


class TokenType(StrEnum):
    ACCESS = "access"
    REFRESH = "refresh"


class TokenPayload:
    """Decoded JWT claims, exposed as a typed value object rather than a raw dict."""

    def __init__(self, subject: str, jti: str, token_type: TokenType, expires_at: datetime) -> None:
        self.subject = subject
        self.jti = jti
        self.token_type = token_type
        self.expires_at = expires_at

    @classmethod
    def from_claims(cls, claims: dict[str, Any]) -> "TokenPayload":
        return cls(
            subject=claims["sub"],
            jti=claims["jti"],
            token_type=TokenType(claims["type"]),
            expires_at=datetime.fromtimestamp(claims["exp"], tz=timezone.utc),
        )


class InvalidTokenError(Exception):
    """Raised when a JWT is malformed, expired, or has an unexpected type."""


def hash_password(plain_password: str) -> str:
    return _password_context.hash(plain_password)


def verify_password(plain_password: str, password_hash: str) -> bool:
    return _password_context.verify(plain_password, password_hash)


def _create_token(subject: str, token_type: TokenType, expires_delta: timedelta, jti: str | None = None) -> tuple[str, str]:
    token_jti = jti or str(uuid.uuid4())
    now = datetime.now(timezone.utc)
    claims = {
        "sub": subject,
        "jti": token_jti,
        "type": token_type.value,
        "iat": now,
        "exp": now + expires_delta,
    }
    encoded = jwt.encode(claims, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)
    return encoded, token_jti


def create_access_token(subject: str) -> tuple[str, str]:
    """Returns (token, jti)."""
    return _create_token(subject, TokenType.ACCESS, timedelta(minutes=settings.access_token_expire_minutes))


def create_refresh_token(subject: str, jti: str | None = None) -> tuple[str, str]:
    """Returns (token, jti)."""
    return _create_token(subject, TokenType.REFRESH, timedelta(days=settings.refresh_token_expire_days), jti=jti)


def decode_token(token: str) -> TokenPayload:
    try:
        claims = jwt.decode(token, settings.jwt_secret_key, algorithms=[settings.jwt_algorithm])
        return TokenPayload.from_claims(claims)
    except jwt.PyJWTError as error:
        raise InvalidTokenError(str(error)) from error
