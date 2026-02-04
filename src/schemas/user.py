from typing import Optional

from pydantic import BaseModel, Field, ConfigDict, EmailStr

class UserBase(BaseModel):
    email: EmailStr = Field(..., min_length=5, max_length=100, description='User Email', examples=['seliukovvladyslav@gmail.com'])
    is_active: bool = True

class UserCreate(UserBase):
    password: str = Field(..., min_length=8, max_length=100, description='User Password', examples=['very_secure_password'])

class UserResponse(UserBase):
    id: int
    is_superuser: bool = False

    model_config = ConfigDict(from_attributes=True)

class UserUpdate(UserBase):
    password: Optional[str] = Field(None, min_length=8, max_length=100, description='User Password', examples=['very_secure_password'])
    is_active: Optional[bool] = Field(None, description='Is User active?', examples=['True'])
    is_superuser: Optional[bool] = Field(None, description='User is super user?', examples=['True'])