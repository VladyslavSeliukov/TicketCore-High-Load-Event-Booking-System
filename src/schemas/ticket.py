from pydantic import BaseModel, ConfigDict, Field, PositiveInt


class TicketBase(BaseModel):
    ticket_type_id: PositiveInt = Field(..., description="Ticket type Id")


class TicketCreate(TicketBase):
    pass


class TicketResponse(TicketBase):
    id: int
    event_title: str

    model_config = ConfigDict(from_attributes=True)

    id: PositiveInt

class TicketUpdate(BaseModel):
    ticket_type_id: int | None = Field(None, description="Ticket type Id")
