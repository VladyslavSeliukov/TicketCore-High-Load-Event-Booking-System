from typing import Annotated

from fastapi import APIRouter
from fastapi.params import Depends

from src.api.deps import PaymentServiceDep, get_current_user
from src.models import Ticket, User
from src.schemas.payment import TicketPaymentSchema

router = APIRouter()


@router.post("/ticket/{ticket_id}", response_model=TicketPaymentSchema, status_code=200)
async def ticket_payment(
    ticket_id: int,
    user: Annotated[User, Depends(get_current_user)],
    payment_service: PaymentServiceDep,
) -> Ticket:
    return await payment_service.pay_for_ticket(ticket_id=ticket_id, owner_id=user.id)
