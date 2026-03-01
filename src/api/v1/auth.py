from typing import Annotated

from fastapi import APIRouter, status
from fastapi.params import Depends
from fastapi.security import OAuth2PasswordRequestForm

from src.api.deps import AuthServiceDep, get_current_user
from src.models.user import User
from src.schemas import PasswordChange, Token, UserCreate, UserResponse

router = APIRouter()


@router.post(
    "/signup", response_model=UserResponse, status_code=status.HTTP_201_CREATED
)
async def register_user(user_in: UserCreate, auth_service: AuthServiceDep) -> User:
    return await auth_service.register(user_in=user_in)


@router.post("/login", response_model=Token)
async def login_for_access_token(
    auth_service: AuthServiceDep,
    form_data: Annotated[OAuth2PasswordRequestForm, Depends()],
) -> dict[str, str]:
    access_token = await auth_service.authenticate(
        email=form_data.username, password=form_data.password
    )

    return {"access_token": access_token, "token_type": "bearer"}


@router.patch(
    "/change-password", response_model=UserResponse, status_code=status.HTTP_201_CREATED
)
async def change_user_password(
    passwords: PasswordChange,
    auth_service: AuthServiceDep,
    current_user: Annotated[User, Depends(get_current_user)],
) -> User:
    return await auth_service.change_password(
        user_id=current_user.id, passwords=passwords
    )
