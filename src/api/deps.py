from src.core.logger import logger

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from pydantic import ValidationError
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from typing import Annotated
from src.core import settings
from src.db.session import get_db
from src.models import User
from src.schemas.token import TokenPayload

reusable_oauth2 = OAuth2PasswordBearer(tokenUrl=f"{settings.API_V1_STR}/auth/login")

DBDep = Annotated[AsyncSession, Depends(get_db)]


async def get_current_user(
    token: Annotated[str, Depends(reusable_oauth2)], session: DBDep
) -> User:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    try:
        jwt_payload = jwt.decode(
            token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM]
        )

        token_data = TokenPayload(**jwt_payload)
        if not token_data.sub:
            logger.info('Auth failed: Token has no "sub" field')
            raise credentials_exception

    except jwt.ExpiredSignatureError:
        logger.info("Auth failed: Token expired")
        raise credentials_exception
    except (jwt.PyJWTError, ValidationError) as e:
        logger.warning(f"Auth failed: Decode error : {e}")
        raise credentials_exception

    try:
        user_id = int(token_data.sub)
    except ValueError:
        logger.warning(f"Auth failed: User Id is not an int: {token_data.sub}")
        raise credentials_exception

    user_query = select(User).where(User.id == user_id)
    user_result = await session.execute(user_query)
    user = user_result.scalar_one_or_none()

    if not user:
        logger.warning(f"Auth failed: User {user_id} not found in DB")
        raise credentials_exception

    return user


async def get_current_superuser(current_user: User = Depends(get_current_user)):
    if not current_user.is_superuser:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="User doesn't have permission"
        )
    return current_user
