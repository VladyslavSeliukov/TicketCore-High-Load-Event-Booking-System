from sqlalchemy import exists, select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from src.core import logger
from src.core.exception import (
    InactiveUserError,
    InvalidCredentialsError,
    UserAlreadyExistsError,
)
from src.core.security import create_access_token, get_password_hash, verify_password
from src.models.user import User
from src.schemas import PasswordChange, UserCreate


class AuthService:
    """Service for managing user authentication, registration, and account security."""

    def __init__(self, session: AsyncSession):
        self.db = session

    async def register(self, user_in: UserCreate) -> User:
        """Register a new user and persist their credentials to the database.

        Args:
            user_in: Schema containing the email and raw password.

        Returns:
            The newly created User instance.

        Raises:
            UserAlreadyExistsError: If a user with the provided email already exists.
            SQLAlchemyError: If the database transaction fails.
        """
        check_query = select(exists().where(User.email == user_in.email))
        if await self.db.scalar(check_query):
            raise UserAlreadyExistsError("User with this email already exists")

        new_user = User(
            email=user_in.email,
            hashed_password=get_password_hash(user_in.password),
            is_active=True,
            is_superuser=False,
        )

        self.db.add(new_user)
        try:
            await self.db.commit()
            await self.db.refresh(new_user)

            logger.info(f"User registered: {new_user.id}")
        except SQLAlchemyError:
            await self.db.rollback()
            raise

        return new_user

    async def authenticate(self, email: str, password: str) -> str:
        """Verify user credentials and generate a JWT access token.

        Args:
            email: User's login email address.
            password: Raw password string.

        Returns:
            A JWT access token valid for subsequent authenticated requests.

        Raises:
            InvalidCredentialsError: If the email or password does not match.
            InactiveUserError: If the user account is disabled.
        """
        user = await self.db.scalar(select(User).where(User.email == email))

        if not user or not verify_password(password, user.hashed_password):
            logger.warning(f"Failed login attempt for {email}")
            raise InvalidCredentialsError("Incorrect email or password")

        if not user.is_active:
            logger.warning(f"Login attempt by inactive user{user.id}")
            raise InactiveUserError("User is inactive")

        logger.info(f"User {user.id} logged in successfully")
        return create_access_token(subject=user.id)

    async def change_password(self, user_id: int, passwords: PasswordChange) -> User:
        """Update the user's password after validating the current one.

        Args:
            user_id: ID of the user performing the password change.
            passwords: Schema containing the old and new password strings.

        Returns:
            The updated User instance.

        Raises:
            InvalidCredentialsError: If the user is not found
            or the old password is incorrect.
            SQLAlchemyError: If the database transaction fails.
        """
        user = await self.db.get(User, user_id)

        if not user:
            raise InvalidCredentialsError("User not found")

        if not verify_password(passwords.old_password, user.hashed_password):
            logger.warning(f"Failed password change for user {user_id}: wrong password")
            raise InvalidCredentialsError("Incorrect old password")

        user.hashed_password = get_password_hash(passwords.new_password)

        try:
            await self.db.commit()
            await self.db.refresh(user)

            logger.info(f"User {user_id} changed password")
        except SQLAlchemyError:
            await self.db.rollback()
            raise

        return user
