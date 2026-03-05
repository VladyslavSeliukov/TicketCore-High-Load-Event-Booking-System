from pydantic import BaseModel, ConfigDict, Field, PositiveInt


class TicketBase(BaseModel):
    ticket_type_id: PositiveInt = Field(..., description="Ticket type Id")


class TicketCreate(TicketBase):
    pass


class TicketResponse(TicketBase):
    model_config = ConfigDict(from_attributes=True)

    id: PositiveInt


class TicketDetailResponse(TicketResponse):
    event_title: str
