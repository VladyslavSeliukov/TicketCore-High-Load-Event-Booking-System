import pytest
from pydantic import ValidationError

from src.schemas import TicketCreate


def test_ticket_params() -> None:
    ticket = TicketCreate(event_id=1, price=100)
    assert ticket.price == 100
    assert ticket.event_id == 1


def test_negative_ticket_price() -> None:
    with pytest.raises(ValidationError):
        TicketCreate(event_id=1, price=-50)


def test_without_ticket_params() -> None:
    with pytest.raises(ValidationError):
        TicketCreate(event_id=1)
