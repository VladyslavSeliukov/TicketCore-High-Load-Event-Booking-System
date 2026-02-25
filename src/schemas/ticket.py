from typing import Optional

from pydantic import BaseModel, Field, ConfigDict


class TicketCreate(BaseModel):
    event_id: int = Field(..., description="Event Id")
    price: int = Field(
        ...,
        gt=0,
        description="Price in cents. Each dollar has 100 cents",
        examples=["10000"],
    )


class TicketResponse(TicketCreate):
    id: int
    event_title: str
    model_config = ConfigDict(from_attributes=True)


class TicketUpdate(TicketCreate):
    event_id: Optional[int] = Field(None, description="Event Id")
    price: Optional[int] = Field(
        None,
        gt=0,
        description="Price in cents. Each dollar has 100 cents",
        examples=["10000"],
    )
