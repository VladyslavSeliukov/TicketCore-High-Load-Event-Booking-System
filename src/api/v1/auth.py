from typing import Annotated

from fastapi import APIRouter, HTTPException, status
from fastapi.params import Depends
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy import select

from src.api.deps import DBDep
from src.core.security import create_access_token, get_password_hash, verify_password
from src.models.user import User
from src.schemas import Token, UserCreate, UserResponse

router = APIRouter()


@router.post(
    "/signup", response_model=UserResponse, status_code=status.HTTP_201_CREATED
)
async def register_user(user_in: UserCreate, session: DBDep) -> User:
    query = select(User).where(User.email == user_in.email)
    result = await session.execute(query)
    existing_user = result.scalar_one_or_none()

    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="User with this email already exists",
        )

    new_user = User(
        email=user_in.email,
        hashed_password=get_password_hash(user_in.password),
        is_active=True,
        is_superuser=False,
    )

    session.add(new_user)
    await session.commit()
    await session.refresh(new_user)

    return new_user


@router.post("/login", response_model=Token)
async def login_for_access_token(
    form_data: Annotated[OAuth2PasswordRequestForm, Depends()], session: DBDep
) -> dict[str, str]:
    unauthorized_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED, headers={"WWW-Authenticate": "Bearer"}
    )

    query = select(User).where(User.email == form_data.username)
    result = await session.execute(query)
    user = result.scalar_one_or_none()

    if not user or not verify_password(form_data.password, user.hashed_password):
        unauthorized_exception.detail = "Incorrect email or password"
        raise unauthorized_exception

    if not user.is_active:
        unauthorized_exception.detail = "User is inactive"
        raise unauthorized_exception

    access_token = create_access_token(subject=user.id)

    return {"access_token": access_token, "token_type": "bearer"}


# @router.put(
#     "/change_password",
#     response_model=UserResponse,
#     status_code=status.HTTP_201_CREATED
# )
# async def change_user_password() -> User:
