from pydantic import BaseModel, Field, ConfigDict


class UserCreate(BaseModel):
    email: str = Field(..., min_length=5, max_length=100, description='User Email', examples=['seliukovvladyslav@gmail.com'])
    password: str = Field(..., min_length=8, max_length=100, description='User Password', examples=['very_secure_password'])
    is_active: bool = True

class UserResponse(UserCreate):
    id: int
    model_config = ConfigDict(from_attributes=True)

class UserUpdate(UserCreate):
    password: str = Field(None, min_length=8, max_length=100, description='User Password', examples=['very_secure_password'])
    is_active: bool = Field(None, description='Is User active?', examples=['True'])
    is_superuser: bool = Field(None, description='User is super user?', examples=['True'])