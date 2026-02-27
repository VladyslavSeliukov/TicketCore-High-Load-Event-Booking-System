from pydantic import BaseModel, ConfigDict, EmailStr, Field


class UserBase(BaseModel):
    email: EmailStr = Field(
        ...,
        min_length=5,
        max_length=100,
        description="User Email",
        examples=["seliukovvladyslav@gmail.com"],
    )
    is_active: bool = True


class UserCreate(UserBase):
    password: str = Field(
        ...,
        min_length=8,
        max_length=100,
        description="User Password",
        examples=["very_secure_password"],
    )


class UserResponse(UserBase):
    id: int
    is_superuser: bool = False

    model_config = ConfigDict(from_attributes=True)


class UserUpdate(BaseModel):
    email: EmailStr | None = Field(
        None,
        min_length=5,
        max_length=100,
        description="User Email",
        examples=["seliukovvladyslav@gmail.com"],
    )
    password: str | None = Field(
        None,
        min_length=8,
        max_length=100,
        description="User Password",
        examples=["very_secure_password"],
    )
    is_active: bool | None = Field(
        None, description="Is User active?", examples=["True"]
    )
    is_superuser: bool | None = Field(
        None, description="User is super user?", examples=["True"]
    )
