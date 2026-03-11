"""Locust load testing script for the TicketCore API."""

import json
import os
import random
import sys
from datetime import UTC, datetime, timedelta
from typing import Any, cast

import jwt
from locust import FastHttpUser, between, events, task
from locust.env import Environment

_event_id_str = os.getenv("TARGET_EVENT_ID")
_ticket_types_str = os.getenv("AVAILABLE_TICKET_TYPES")

if not _ticket_types_str or not _event_id_str:
    print("ERROR: all variable is required.")
    sys.exit(1)

TARGET_EVENT_ID: int = int(_event_id_str)
AVAILABLE_TICKET_TYPES: list[int] = [
    int(t_id.strip()) for t_id in _ticket_types_str.split(",") if t_id.strip().isdigit()
]

SECRET_KEY = "2b55886afc889358509ae2a6fe93ac8b881d7985b1984bf71b9d41e5a0c1a281"
ALGORITHM = "HS256"


@events.test_start.add_listener
def on_test_start(environment: Environment, **kwargs: Any) -> None:
    """Ensure environment is sane before Locust starts spawning users."""
    if not TARGET_EVENT_ID or not AVAILABLE_TICKET_TYPES:
        environment.runner.quit()


class RammsteinFan(FastHttpUser):
    """Simulated user behavior for high-load event ticketing."""

    wait_time = between(0.1, 0.5)

    def __init__(self, environment: Environment) -> None:
        super().__init__(environment)
        self.headers: dict[str, str] = {"Content-Type": "application/json"}

    def on_start(self) -> None:
        """Execute setup operations when a simulated user spawns."""
        user_id = random.randint(1, 10000)

        token_payload = {
            "sub": str(user_id),
            "exp": datetime.now(UTC) + timedelta(minutes=30),
        }

        token = cast(str, jwt.encode(token_payload, SECRET_KEY, algorithm=ALGORITHM))
        self.headers["Authorization"] = f"Bearer {token}"

    @task(4)
    def browse_event(self) -> None:
        """Simulate a user viewing the target event's details."""
        self.client.get(
            f"/api/v1/events/{TARGET_EVENT_ID}",
            headers=self.headers,
            name="/api/v1/events/[id]",
        )

    @task(1)
    def attempt_purchase(self) -> None:
        """Simulate a user attempting to reserve tickets for the event."""
        ticket_type_id = random.choice(AVAILABLE_TICKET_TYPES)
        payload: dict[str, Any] = {
            "event_id": TARGET_EVENT_ID,
            "ticket_type_id": ticket_type_id,
            "quantity": random.randint(1, 2),
        }

        with self.client.post(
            "/api/v1/tickets/",
            json=payload,
            headers=self.headers,
            name="/api/v1/tickets/",
            catch_response=True,
        ) as response:
            if response.status_code in (200, 201):
                response.success()
            elif response.status_code in (400, 404, 409):
                try:
                    error_detail = response.json().get("detail", "").lower()
                    if any(
                        kw in error_detail
                        for kw in ["sold out", "not enough", "unavailable"]
                    ):
                        response.success()
                    else:
                        response.failure(f"Unexpected business error: {error_detail}")
                except json.JSONDecodeError:
                    response.failure(f"Non-JSON error response: {response.text}")
            elif response.status_code == 422:
                response.failure(f"Pydantic Validation Error: {response.text}")
            else:
                response.failure(f"HTTP {response.status_code}: {response.text}")
