import asyncio

from sqlalchemy import select

from src.core.security import get_password_hash
from src.db.session import AsyncSessionLocal
from src.models import User


async def create_test_superuser() -> None:
    email, password = "seliukovvladyslav@gmail.com", "very_secure_password"

    async with AsyncSessionLocal() as session:
        query = select(User).where(User.email == email)
        result = await session.execute(query)
        if result.scalar_one_or_none():
            print(f"User with {email} email already exist")
            return

        admin = User(
            email=email,
            hashed_password=get_password_hash(password),
            is_active=True,
            is_superuser=True,
        )
        session.add(admin)
        await session.commit()
        print(f"Superuser {email} created")


if __name__ == "__main__":
    asyncio.run(create_test_superuser())
