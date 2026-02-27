from pydantic import BaseModel, ConfigDict, Field


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


class TicketUpdate(BaseModel):
    event_id: int | None = Field(None, description="Event Id")
    price: int | None = Field(
        None,
        gt=0,
        description="Price in cents. Each dollar has 100 cents",
        examples=["10000"],
    )
