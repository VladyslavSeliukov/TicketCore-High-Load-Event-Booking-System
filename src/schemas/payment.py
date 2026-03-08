from pydantic import BaseModel, ConfigDict, PositiveInt

from src.models.ticket import TicketStatus


class TicketPaymentSchema(BaseModel):
    """Response payload confirming a successful ticket payment and status update."""

    model_config = ConfigDict(from_attributes=True)

    id: PositiveInt
    status: TicketStatus
