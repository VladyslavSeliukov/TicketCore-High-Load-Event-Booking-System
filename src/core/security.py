from datetime import datetime, timedelta
from typing import Any, cast

import jwt
from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError

from src.core import settings

ph = PasswordHasher()


def verify_password(plain_password: str, hashed_password: str) -> bool:
    try:
        return bool(ph.verify(hashed_password, plain_password))
    except VerifyMismatchError:
        return False


def get_password_hash(password: str) -> str:
    return str(ph.hash(password=password))


def create_access_token(
    subject: str | Any, expires_delta: timedelta | None = None
) -> str:
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(
            minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES
        )

    to_encode = {"exp": expire, "sub": str(subject)}
    encoded_jwt = jwt.encode(
        to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM
    )

    return cast(str, encoded_jwt)
