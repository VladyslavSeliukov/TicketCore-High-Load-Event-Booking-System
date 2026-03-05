from pydantic import (
    BaseModel,
    ConfigDict,
    EmailStr,
    Field,
    PositiveInt,
    field_validator,
)


class UserBase(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    email: EmailStr = Field(
        ...,
        min_length=5,
        max_length=254,
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

    @field_validator("email", mode="before")
    @classmethod
    def lowercase_email(cls, v: str) -> str:
        if isinstance(v, str):
            return v.lower()
        return v


class UserResponse(UserBase):
    id: PositiveInt
    is_superuser: bool = False

    model_config = ConfigDict(from_attributes=True)


class UserUpdate(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    email: EmailStr | None = Field(
        None,
        min_length=5,
        max_length=254,
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

    @field_validator("email", mode="before")
    @classmethod
    def lowercase_email(cls, v: str | None) -> str | None:
        if isinstance(v, str):
            return v.lower()
        return v


class PasswordChange(BaseModel):
    old_password: str
    model_config = ConfigDict(str_strip_whitespace=True)

    new_password: str = Field(
        min_length=8,
        max_length=100,
        description="New Password",
        examples=["very_secure_password"],
    )
