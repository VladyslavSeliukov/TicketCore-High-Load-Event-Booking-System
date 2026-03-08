from pydantic import AwareDatetime, BaseModel, ConfigDict, Field, PositiveInt

from src.schemas.ticket_type import TicketTypeResponse


class EventBase(BaseModel):
    """Base schema containing common event attributes."""

    model_config = ConfigDict(str_strip_whitespace=True)

    title: str = Field(
        ...,
        min_length=1,
        max_length=100,
        description="Title of the event",
        examples=["Korn Europe Tour 2026"],
    )
    date: AwareDatetime = Field(
        ..., description="Date and time of the event", examples=["2026-01-01T14:15:45Z"]
    )

    country: str = Field(
        ...,
        min_length=1,
        max_length=100,
        description="Country of the event",
        examples=["Poland"],
    )
    city: str = Field(
        ...,
        min_length=1,
        max_length=100,
        description="City of the event",
        examples=["Wroclaw"],
    )
    street_address: str = Field(
        ...,
        min_length=1,
        max_length=100,
        description="Street address of the event",
        examples=["Sucha 1"],
    )


class EventCreate(EventBase):
    """Payload schema for creating a new event."""

    pass


class EventResponse(EventBase):
    """Basic public representation of an event returned by the API."""

    model_config = ConfigDict(from_attributes=True)

    id: PositiveInt


class EventDetailResponse(EventResponse):
    """Detailed representation of an event, including its available ticket types."""

    ticket_types: list[TicketTypeResponse]

    model_config = ConfigDict(from_attributes=True)


class EventUpdate(BaseModel):
    """Payload schema for partially updating an event's attributes."""

    model_config = ConfigDict(str_strip_whitespace=True)

    title: str | None = Field(
        None,
        min_length=1,
        max_length=100,
        description="Title of the event",
        examples=["Korn Europe Tour 2026"],
    )
    date: AwareDatetime | None = Field(
        None, description="Data of the event", examples=["2026-01-01T14:15:45Z"]
    )

    country: str | None = Field(
        None,
        min_length=1,
        max_length=100,
        description="Country of the event",
        examples=["Poland"],
    )
    city: str | None = Field(
        None,
        min_length=1,
        max_length=100,
        description="City of the event",
        examples=["Wroclaw"],
    )
    street_address: str | None = Field(
        None,
        min_length=1,
        max_length=100,
        description="Street address of the event",
        examples=["Sucha 1"],
    )
