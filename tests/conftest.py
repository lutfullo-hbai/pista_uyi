import os
from collections.abc import AsyncGenerator
from unittest.mock import AsyncMock, MagicMock

os.environ.setdefault("BOT_TOKEN", "1234567890:AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA")
os.environ.setdefault("CHANNEL_ID", "@test_channel")
os.environ.setdefault("DATABASE_URL", "postgresql://test:test@localhost:5432/test_qurut")
os.environ.setdefault("WEB_APP_URL", "https://test.example.com")
os.environ.setdefault("ADMIN_IDS", "[123, 456]")

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

from bot.services.database import db as real_db
from web.server import app


@pytest.fixture(autouse=True)
def mock_db():
    conn = AsyncMock()
    conn.fetch = AsyncMock(return_value=[])
    conn.fetchrow = AsyncMock(return_value=None)
    conn.fetchval = AsyncMock(return_value=0)
    cm = AsyncMock()
    cm.__aenter__.return_value = conn
    real_db.pool = AsyncMock()
    real_db.pool.acquire = MagicMock(return_value=cm)
    real_db.connect = AsyncMock()
    real_db.close = AsyncMock()
    yield


@pytest_asyncio.fixture
async def client() -> AsyncGenerator[AsyncClient, None]:
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


@pytest.fixture
def sample_order():
    return {
        "id": 1,
        "user_id": 123,
        "user_name": "Ali",
        "phone": "+998901234567",
        "address": "Toshkent, Chilonzor",
        "total_amount": 50000.0,
        "created_at": None,
        "items": [
            {"product_name": "Qurut", "quantity": 2, "price": 15000.0},
            {"product_name": "Non", "quantity": 1, "price": 20000.0},
        ],
    }
