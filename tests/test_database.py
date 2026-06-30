import pytest


def test_db_import():
    from bot.services.database import db
    assert db is not None
    assert hasattr(db, "pool")
    assert hasattr(db, "connect")
    assert hasattr(db, "close")
    assert hasattr(db, "get_categories")
    assert hasattr(db, "get_all_products")
    assert hasattr(db, "create_order")
    assert hasattr(db, "get_order")
    assert hasattr(db, "get_warehouse_items")
    assert hasattr(db, "add_warehouse_stock")
    assert hasattr(db, "remove_warehouse_stock")
    assert hasattr(db, "get_warehouse_stats")
    assert hasattr(db, "create_daily_sale")
    assert hasattr(db, "get_daily_sales")
    assert hasattr(db, "get_daily_sales_stats")
    assert hasattr(db, "get_warehouse_dashboard_stats")
