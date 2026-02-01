from fastapi import APIRouter, status, HTTPException
from fastapi.params import Depends
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.sql.annotation import Annotated

from src.core.security import get_password_hash, verify_password
from src.db.session import get_db
from src.models.user import User
from src.schemas import UserResponse, UserCreate

router = APIRouter()

@router.post('/', response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def register_user(
        user_in: UserCreate,
        session: AsyncSession = Depends(get_db)
):
    query = select(User).where(User.email == user_in.email)
    result = await session.execute(query)
    existing_user = result.scalar_one_or_none()

    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail='User with this email already exists'
        )ƒ

    new_user = User(
        email=user_in.email,
        hashed_password = get_password_hash(user_in.password),
        is_active = True,
        is_superuser = False
    )

    session.add(new_user)
    await session.commit()
    await session.refresh(new_user)

    return new_user

