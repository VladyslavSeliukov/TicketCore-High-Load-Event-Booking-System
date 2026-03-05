from pydantic import BaseModel, ConfigDict, Field, NonNegativeInt, PositiveInt


class TicketTypeBase(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    name: str = Field(
        ...,
        min_length=1,
        max_length=50,
        description="Ticket type name",
        examples=["VIP", "Standard"],
    )
    price: NonNegativeInt = Field(
        ..., ge=0, description="Price in cents", examples=[10000]
    )

    tickets_quantity: int = Field(
        ..., gt=0, description="Quantity of tickets of this type"
    )


class TicketTypeCreate(TicketTypeBase):
    event_id: PositiveInt = Field(..., description="Event id")


class TicketTypeResponse(TicketTypeCreate):
    model_config = ConfigDict(from_attributes=True)

    id: PositiveInt


class TicketTypeDetailResponse(TicketTypeResponse):
    tickets_sold: NonNegativeInt


class TicketTypeUpdate(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    name: str | None = Field(
        None,
        min_length=1,
        max_length=50,
        description="Ticket type name",
        examples=["VIP", "Standard"],
    )
    price: NonNegativeInt | None = Field(
        None, ge=0, description="Price in cents", examples=[10000]
    )
    tickets_quantity: PositiveInt | None = Field(
        None, gt=0, description="Quantity of tickets of this type"
    )
