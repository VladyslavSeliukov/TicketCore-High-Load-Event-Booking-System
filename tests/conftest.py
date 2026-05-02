import asyncio
import uuid
from collections.abc import Generator
from pathlib import Path

import pytest
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent

load_dotenv(BASE_DIR / ".env")


load_dotenv()


@pytest.fixture(scope="session")
def event_loop() -> Generator[asyncio.AbstractEventLoop, None, None]:
    policy = asyncio.get_event_loop_policy()
    loop = policy.new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
def idempotency_header() -> dict[str, str]:
    return {"Idempotency-Key": str(uuid.uuid4())}
