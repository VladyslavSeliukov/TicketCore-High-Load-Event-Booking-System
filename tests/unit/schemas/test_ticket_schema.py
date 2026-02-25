import pytest
from pydantic import ValidationError
from src.schemas import TicketCreate, TicketUpdate


def test_ticket_params():
    ticket = TicketCreate(event_id=1, price=100)
    assert ticket.price == 100
    assert ticket.event_id == 1


def test_negative_ticket_price():
    with pytest.raises(ValidationError):
        TicketCreate(event_id=1, price=-50)


def test_without_ticket_params():
    with pytest.raises(ValidationError):
        TicketCreate(event_id=1)
