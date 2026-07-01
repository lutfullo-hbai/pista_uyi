import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_health(client: AsyncClient):
    resp = await client.get("/health")
    assert resp.status_code in (200, 503)


@pytest.mark.asyncio
async def test_get_categories(client: AsyncClient):
    resp = await client.get("/api/categories")
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)


@pytest.mark.asyncio
async def test_get_products(client: AsyncClient):
    resp = await client.get("/api/products")
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)


@pytest.mark.asyncio
async def test_get_warehouse(client: AsyncClient):
    resp = await client.get("/api/warehouse")
    assert resp.status_code == 200
    data = resp.json()
    assert "items" in data
    assert "stats" in data


@pytest.mark.asyncio
async def test_create_warehouse_item(client: AsyncClient):
    resp = await client.post("/api/warehouse", json={"name": "Test mahsulot", "unit": "dona", "quantity": 10})
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "created"
    assert "id" in data


@pytest.mark.asyncio
async def test_get_warehouse_transactions(client: AsyncClient):
    resp = await client.get("/api/warehouse/transactions")
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)


@pytest.mark.asyncio
async def test_get_warehouse_stats(client: AsyncClient):
    resp = await client.get("/api/warehouse/stats")
    assert resp.status_code == 200


@pytest.mark.asyncio
async def test_get_warehouse_period_stats(client: AsyncClient):
    for period in ("today", "week", "month", "year", "all"):
        resp = await client.get(f"/api/warehouse/stats/{period}")
        assert resp.status_code == 200

    resp = await client.get("/api/warehouse/stats/invalid")
    assert resp.status_code == 400


@pytest.mark.asyncio
async def test_get_daily_sales(client: AsyncClient):
    resp = await client.get("/api/daily-sales")
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)


@pytest.mark.asyncio
async def test_create_daily_sale(client: AsyncClient):
    payload = {
        "total_amount": 500000.0,
        "notes": "Test savdo",
        "recorded_by": 123,
    }
    resp = await client.post("/api/daily-sales", json=payload)
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "created"
    assert "id" in data


@pytest.mark.asyncio
async def test_create_daily_sale_with_date(client: AsyncClient):
    payload = {
        "total_amount": 300000.0,
        "sale_date": "2025-03-15",
        "notes": "Test",
        "recorded_by": 123,
    }
    resp = await client.post("/api/daily-sales", json=payload)
    assert resp.status_code == 200


@pytest.mark.asyncio
async def test_delete_daily_sale_invalid_id(client: AsyncClient):
    resp = await client.delete("/api/daily-sales/0")
    assert resp.status_code == 400


@pytest.mark.asyncio
async def test_get_daily_sales_stats(client: AsyncClient):
    resp = await client.get("/api/daily-sales/stats")
    assert resp.status_code == 200
    stats = resp.json()
    assert "period" in stats
    assert "total_sales" in stats
    assert "total_amount" in stats


@pytest.mark.asyncio
async def test_get_daily_sales_period_stats(client: AsyncClient):
    for period in ("today", "week", "month", "year", "all"):
        resp = await client.get(f"/api/daily-sales/stats/{period}")
        assert resp.status_code == 200

    resp = await client.get("/api/daily-sales/stats/invalid")
    assert resp.status_code == 400
