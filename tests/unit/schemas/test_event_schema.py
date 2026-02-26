from datetime import datetime
from typing import Any

import pytest
from pydantic import ValidationError
from utils import get_missing_field_cases

from src.schemas import EventCreate


class TestEventCreateSchemaValidation:
    VALID_PAYLOAD = {
        "title": "Korn Europe Tour 2026",
        "date": "2026-01-01T14:15:45",
        "tickets_quantity": "100",
        "country": "Poland",
        "city": "Wroclaw",
        "street_address": "Sucha 1",
    }

    def test_valid(self) -> None:
        event: EventCreate = EventCreate(**self.VALID_PAYLOAD)

        assert event.title == self.VALID_PAYLOAD["title"]
        assert event.date == datetime.fromisoformat(self.VALID_PAYLOAD["date"])
        assert event.tickets_quantity == int(self.VALID_PAYLOAD["tickets_quantity"])
        assert event.country == self.VALID_PAYLOAD["country"]
        assert event.city == self.VALID_PAYLOAD["city"]
        assert event.street_address == self.VALID_PAYLOAD["street_address"]

    @pytest.mark.parametrize(
        "missing_field, payload", get_missing_field_cases(VALID_PAYLOAD)
    )
    def test_with_missing_field(
        self, missing_field: str, payload: dict[str, Any]
    ) -> None:
        with pytest.raises(ValidationError) as exc:
            EventCreate(**payload)

        if missing_field != "all":
            assert any(e["loc"][0] == missing_field for e in exc.value.errors())

    @pytest.mark.parametrize(
        "field, invalid_value, error_message_part",
        [
            ("title", "a" * 101, "String should have at most 100 characters"),
            ("title", "", "String should have at least 1 character"),
            ("tickets_quantity", 0, "Input should be greater than 0"),
            ("tickets_quantity", -10, "Input should be greater than 0"),
            ("tickets_quantity", "not-a-number", "Input should be a valid integer"),
            ("date", "not-a-date", "Input should be a valid datetime"),
            ("city", "", "String should have at least 1 character"),
            ("country", "", "String should have at least 1 character"),
            ("street_address", "", "String should have at least 1 character"),
        ],
    )
    def test_invalid_cases(
        self, field: str, invalid_value: str, error_message_part: str
    ) -> None:
        payload = self.VALID_PAYLOAD.copy()
        payload[field] = invalid_value

        with pytest.raises(ValidationError) as exc:
            EventCreate(**payload)

        errors = exc.value.errors()
        for error in errors:
            if error["loc"][0] == field:
                assert error_message_part in error["msg"]
                return
        pytest.fail("Error not found")
