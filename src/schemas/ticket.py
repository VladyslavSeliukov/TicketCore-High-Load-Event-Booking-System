from pydantic import BaseModel, ConfigDict, Field


class TicketBase(BaseModel):
    ticket_type_id: int = Field(..., description="Ticket type Id")


class TicketCreate(TicketBase):
    pass


class TicketResponse(TicketBase):
    id: int
    event_title: str

    model_config = ConfigDict(from_attributes=True)


class TicketUpdate(BaseModel):
    ticket_type_id: int | None = Field(None, description="Ticket type Id")
