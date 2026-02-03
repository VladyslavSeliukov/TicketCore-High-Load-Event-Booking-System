from typing import Optional

from pydantic import BaseModel, Field

class Token(BaseModel):
    access_token: str
    token_type: str

class TokenPayload(BaseModel):
    sub: Optional[str] = Field(None, description='User Id')