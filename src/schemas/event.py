from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from src.schemas.ticket_type import TicketTypeResponse


class EventBase(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    title: str = Field(
        ...,
        min_length=1,
        max_length=100,
        description="Title of the event",
        examples=["Korn Europe Tour 2026"],
    )
    date: datetime = Field(
        ..., description="Date and time of the event", examples=["2026-01-01T14:15:45"]
    )

    country: str = Field(
        ..., min_length=1, description="Country of the event", examples=["Poland"]
    )
    city: str = Field(
        ..., min_length=1, description="City of the event", examples=["Wroclaw"]
    )
    street_address: str = Field(
        ...,
        min_length=1,
        description="Street address of the event",
        examples=["Sucha 1"],
    )


class EventCreate(EventBase):
    pass


class EventResponse(EventBase):
    id: int
    ticket_types: list[TicketTypeResponse]

    model_config = ConfigDict(from_attributes=True)


class EventUpdate(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    title: str | None = Field(
        None,
        min_length=1,
        max_length=100,
        description="Title of the event",
        examples=["Korn Europe Tour 2026"],
    )
    date: datetime | None = Field(
        None, description="Data of the event", examples=["2026-01-01T14:15:45"]
    )

    country: str | None = Field(
        None, min_length=1, description="Country of the event", examples=["Poland"]
    )
    city: str | None = Field(
        None, min_length=1, description="City of the event", examples=["Wroclaw"]
    )
    street_address: str | None = Field(
        None,
        min_length=1,
        description="Street address of the event",
        examples=["Sucha 1"],
    )
