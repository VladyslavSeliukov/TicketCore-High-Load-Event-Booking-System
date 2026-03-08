from pydantic import BaseModel, ConfigDict, PositiveInt

from src.models.ticket import TicketStatus


class TicketPaymentSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: PositiveInt
    status: TicketStatus
