from pydantic import BaseModel, Field


class Token(BaseModel):
    """OAuth2 standard response schema for access tokens."""

    access_token: str
    token_type: str


class TokenPayload(BaseModel):
    """Internal schema for decoding and validating JWT payload claims."""

    sub: str = Field(..., description="User Id")
