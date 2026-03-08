from datetime import UTC, datetime, timedelta
from typing import Any, cast

import jwt
from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError

from src.core import settings

ph = PasswordHasher()


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a plaintext password against its Argon2 hash.

    Args:
        plain_password: The raw password provided by the user.
        hashed_password: The stored Argon2 hash to compare against.

    Returns:
        True if the password matches the hash, False otherwise.
    """
    try:
        return bool(ph.verify(hashed_password, plain_password))
    except VerifyMismatchError:
        return False


def get_password_hash(password: str) -> str:
    """Generate a secure Argon2 hash for a plaintext password.

    Args:
        password: The raw password to hash.

    Returns:
        The resulting hash string.
    """
    return str(ph.hash(password=password))


def create_access_token(
    subject: str | Any, expires_delta: timedelta | None = None
) -> str:
    """Generate a new JWT access token for a given subject.

    Args:
        subject: The identifier (usually user ID) to embed in the token claim.
        expires_delta: Optional custom expiration time. If not provided,
            defaults to the application settings.

    Returns:
        The encoded JWT string.
    """
    if expires_delta:
        expire = datetime.now(UTC) + expires_delta
    else:
        expire = datetime.now(UTC) + timedelta(
            minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES
        )

    to_encode = {"exp": expire, "sub": str(subject)}
    encoded_jwt = jwt.encode(
        to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM
    )

    return cast(str, encoded_jwt)
