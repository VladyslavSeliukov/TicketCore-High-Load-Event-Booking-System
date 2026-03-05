from pydantic import BaseModel, ConfigDict, Field


class TicketTypeBase(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    name: str = Field(
        ...,
        min_length=1,
        max_length=50,
        description="Ticket type name",
        examples=["VIP", "Standard"],
    )
    price: int = Field(..., ge=0, description="Price in cents", examples=[10000])

    tickets_quantity: int = Field(
        ..., gt=0, description="Quantity of tickets of this type"
    )


class TicketTypeCreate(TicketTypeBase):
    event_id: int = Field(..., description="Event id")


class TicketTypeResponse(TicketTypeCreate):
    id: int
    tickets_sold: int
    model_config = ConfigDict(from_attributes=True)


class TicketTypeUpdate(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    name: str | None = Field(
        None,
        min_length=1,
        max_length=50,
        description="Ticket type name",
        examples=["VIP", "Standard"],
    )
    price: int | None = Field(
        None, ge=0, description="Price in cents", examples=[10000]
    )
    tickets_quantity: int | None = Field(
        None, gt=0, description="Quantity of tickets of this type"
    )
