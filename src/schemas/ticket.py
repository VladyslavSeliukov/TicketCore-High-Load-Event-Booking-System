from pydantic import BaseModel, ConfigDict, Field, PositiveInt

from src.models.ticket import TicketStatus


class TicketBase(BaseModel):
    ticket_type_id: PositiveInt = Field(..., description="Ticket type Id")


class TicketCreate(TicketBase):
    pass


class TicketResponse(TicketBase):
    model_config = ConfigDict(from_attributes=True)

    id: PositiveInt
    status: TicketStatus


class TicketDetailResponse(TicketResponse):
    event_title: str
