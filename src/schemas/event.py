from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class EventCreate(BaseModel):
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
    tickets_quantity: int = Field(
        ..., gt=0, description="Quantity of the tickets", examples=[100]
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


class EventResponse(EventCreate):
    id: int
    tickets_sold: int
    model_config = ConfigDict(from_attributes=True)


class EventUpdate(EventCreate):
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
    tickets_quantity: int | None = Field(
        None, gt=0, description="Quantity of the tickets", examples=[100]
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
