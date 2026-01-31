from datetime import datetime

import pytest
from pydantic import ValidationError
from src.schemas import EventCreate, EventUpdate

def test_event_params():
    current_date = datetime.now()
    event: EventCreate = EventCreate(
        title='test event',
        date=current_date,
        tickets_quantity=50,
        country='test country',
        city='test city',
        street_address='test street address'
    )

    assert event.title == 'test event'
    assert event.date == current_date
    assert event.tickets_quantity == 50
    assert event.country == 'test country'
    assert event.city == 'test city'
    assert event.street_address == 'test street address'

def test_with_negative_tickets_quantity():
    current_date = datetime.now()
    with pytest.raises(ValidationError):
        EventCreate(
            title='test event',
            date=current_date,
            tickets_quantity=-50,
            country='test country',
            city='test city',
            street_address='test street address'
        )

def test_without_event_params():
    with pytest.raises(ValidationError):
        EventCreate(
            title='test event',
        )