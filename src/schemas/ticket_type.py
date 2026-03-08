from pydantic import BaseModel, ConfigDict, Field, NonNegativeInt, PositiveInt


class TicketTypeBase(BaseModel):
    """Base schema containing common ticket type attributes."""

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
    """Payload schema for creating a new ticket pricing category for an event."""

    event_id: PositiveInt = Field(..., description="Event id")


class TicketTypeResponse(TicketTypeCreate):
    """Basic representation of a ticket type returned by the API."""

    model_config = ConfigDict(from_attributes=True)

    id: PositiveInt


class TicketTypeDetailResponse(TicketTypeResponse):
    """Detailed ticket type view, exposing real-time sales statistics."""

    tickets_sold: NonNegativeInt


class TicketTypeUpdate(BaseModel):
    """Payload schema for modifying an existing ticket type's pricing or capacity."""

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
