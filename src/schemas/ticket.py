from pydantic import BaseModel, ConfigDict, Field, PositiveInt

from src.models.ticket import TicketStatus


class TicketBase(BaseModel):
    """Base schema containing common ticket attributes."""

    ticket_type_id: PositiveInt = Field(..., description="Ticket type Id")


class TicketCreate(TicketBase):
    """Payload schema for reserving a new ticket of a specific type."""

    pass


class TicketResponse(TicketBase):
    """Representation of a ticket, including its current reservation status."""

    model_config = ConfigDict(from_attributes=True)

    id: PositiveInt
    status: TicketStatus


class TicketDetailResponse(TicketResponse):
    """Detailed ticket view, including the resolved title of the associated event."""

    event_title: str
