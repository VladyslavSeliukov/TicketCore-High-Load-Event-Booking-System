from pydantic import BaseModel, Field


class Token(BaseModel):
    access_token: str
    token_type: str


class TokenPayload(BaseModel):
    sub: str | None = Field(None, description="User Id")
