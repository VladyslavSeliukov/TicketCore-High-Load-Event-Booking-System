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
async def register_user(
    user_in: UserCreate, auth_service: AuthServiceDep
) -> UserResponse:
    """Register a new user account.

    Creates a new user record in the database with a hashed password.

    Args:
        user_in: The user's registration details (email and password).
        auth_service: Injected authentication service dependency.

    Returns:
        UserResponse DTO containing the newly created user data.
    """
    return await auth_service.register(user_in=user_in)


@router.post("/login", response_model=Token)
async def login_for_access_token(
    auth_service: AuthServiceDep,
    form_data: Annotated[OAuth2PasswordRequestForm, Depends()],
) -> dict[str, str]:
    """Authenticate a user and issue an OAuth2 access token.

    Validates the provided email and password. If successful, returns a JWT
    bearer token used for authorizing subsequent requests.

    Args:
        auth_service: Injected authentication service dependency.
        form_data: Standard OAuth2 password form data (username maps to email).

    Returns:
        A dictionary containing the 'access_token' and 'token_type'.
    """
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
) -> UserResponse:
    """Change the password for the currently authenticated user.

    Requires the user to provide their current password for verification
    before applying the new one.

    Args:
        passwords: The old password and the new password.
        auth_service: Injected authentication service dependency.
        current_user: The authenticated user making the request.

    Returns:
        UserResponse DTO containing the updated user data.
    """
    return await auth_service.change_password(
        user_id=current_user.id, passwords=passwords
    )
