from typing import Annotated

from fastapi import APIRouter, status
from fastapi.params import Depends

from src.api.deps import PaymentServiceDep, get_current_user
from src.models import User
from src.schemas.payment import TicketPaymentSchema

router = APIRouter()


@router.post(
    "/ticket/{ticket_id}",
    response_model=TicketPaymentSchema,
    status_code=status.HTTP_200_OK,
)
async def ticket_payment(
    ticket_id: int,
    user: Annotated[User, Depends(get_current_user)],
    payment_service: PaymentServiceDep,
) -> TicketPaymentSchema:
    """Process a payment for a reserved ticket.

    Transitions the ticket status to 'SOLD'. Users can only pay for
    their own reserved tickets.

    Args:
        ticket_id: The unique identifier of the ticket to pay for.
        user: The authenticated user making the payment.
        payment_service: Injected payment service dependency.

    Returns:
        TicketPaymentSchema DTO reflecting the successful payment and 'SOLD' status.
    """
    return await payment_service.pay_for_ticket(ticket_id=ticket_id, owner_id=user.id)
