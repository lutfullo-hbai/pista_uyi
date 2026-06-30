from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field

from bot.services.database import db
from bot.services.notifier import notify_channel
from bot.utils.validators import validate_phone, validate_address, validate_quantity
from bot.utils.logger import get_logger

router = APIRouter()
logger = get_logger(__name__)


# ── Response Models ──

class OrderItemRequest(BaseModel):
    product_id: int
    name: str
    quantity: int = Field(gt=0, le=999)
    price: float = Field(gt=0)


class OrderRequest(BaseModel):
    user_id: int
    user_name: str | None = None
    phone: str
    address: str
    items: list[OrderItemRequest]


class CartItemRequest(BaseModel):
    product_id: int
    quantity: int = Field(gt=0, le=999)


class ErrorResponse(BaseModel):
    detail: str


# ── Health Check ──

@router.get("/health")
async def health():
    """Health check endpoint."""
    try:
        async with db.pool.acquire() as conn:
            await conn.fetchval("SELECT 1")
        return {"status": "ok", "database": "connected"}
    except Exception as e:
        logger.error("Health check failed: %s", e)
        return {"status": "error", "database": "disconnected"}, 503


# ── Categories & Products ──

@router.get("/api/categories")
async def get_categories():
    """Get all product categories."""
    try:
        categories = await db.get_categories()
        return categories
    except Exception as e:
        logger.error("Failed to get categories: %s", e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to fetch categories",
        )


@router.get("/api/products")
async def get_products():
    """Get all available products."""
    try:
        products = await db.get_all_products()
        return products
    except Exception as e:
        logger.error("Failed to get products: %s", e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to fetch products",
        )


@router.get("/api/products/{category_id}")
async def get_products_by_category(category_id: int):
    """Get products by category."""
    if category_id <= 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid category ID",
        )
    
    try:
        products = await db.get_products_by_category(category_id)
        return products
    except Exception as e:
        logger.error("Failed to get products for category %d: %s", category_id, e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to fetch products",
        )


# ── Orders ──

@router.get("/api/orders/user/{user_id}")
async def get_user_orders(user_id: int):
    """Get all orders for a user."""
    if user_id <= 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid user ID",
        )
    
    try:
        orders = await db.get_orders_by_user(user_id)
        return orders
    except Exception as e:
        logger.error("Failed to get orders for user %d: %s", user_id, e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to fetch orders",
        )


@router.post("/api/orders", response_model=dict)
async def create_order(data: OrderRequest):
    """Create new order."""
    # Validate input
    if not data.items:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Order must contain at least one item",
        )
    
    if not validate_phone(data.phone):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid phone number format",
        )
    
    if not validate_address(data.address):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid address (must be 3-500 characters)",
        )
    
    for item in data.items:
        if not validate_quantity(item.quantity):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid quantity for product {item.product_id}",
            )
    
    try:
        items = [item.model_dump() for item in data.items]
        order_id = await db.create_order(
            user_id=data.user_id,
            user_name=data.user_name,
            phone=data.phone,
            address=data.address,
            items=items,
        )
        
        order = await db.get_order(order_id)
        if order:
            await notify_channel(order)
            logger.info("Order created: #%d for user %d", order_id, data.user_id)
        
        return {"order_id": order_id, "status": "created"}
    
    except Exception as e:
        logger.error("Failed to create order for user %d: %s", data.user_id, e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create order",
        )


# ── Cart Endpoints ──

@router.get("/api/cart/{user_id}")
async def get_cart(user_id: int):
    """Get user's cart items."""
    if user_id <= 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid user ID",
        )
    
    try:
        items = await db.get_cart_items(user_id)
        cart_total = await db.get_cart_total(user_id)
        return {
            "items": items,
            "item_count": cart_total["item_count"],
            "total_amount": cart_total["total_amount"],
        }
    except Exception as e:
        logger.error("Failed to get cart for user %d: %s", user_id, e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to fetch cart",
        )


@router.post("/api/cart/{user_id}")
async def add_to_cart(user_id: int, item: CartItemRequest):
    """Add item to cart."""
    if user_id <= 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid user ID",
        )
    
    if not validate_quantity(item.quantity):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid quantity",
        )
    
    try:
        success = await db.add_to_cart(user_id, item.product_id, item.quantity)
        if not success:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Product not available or invalid",
            )
        
        logger.info("Added to cart - user %d, product %d, qty %d", 
                   user_id, item.product_id, item.quantity)
        
        cart_total = await db.get_cart_total(user_id)
        return {
            "status": "added",
            "item_count": cart_total["item_count"],
            "total_amount": cart_total["total_amount"],
        }
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to add to cart for user %d: %s", user_id, e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to add to cart",
        )


@router.delete("/api/cart/{user_id}/{product_id}")
async def remove_from_cart(user_id: int, product_id: int):
    """Remove item from cart."""
    if user_id <= 0 or product_id <= 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid user ID or product ID",
        )
    
    try:
        success = await db.remove_from_cart(user_id, product_id)
        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Item not found in cart",
            )
        
        logger.info("Removed from cart - user %d, product %d", user_id, product_id)
        
        cart_total = await db.get_cart_total(user_id)
        return {
            "status": "removed",
            "item_count": cart_total["item_count"],
            "total_amount": cart_total["total_amount"],
        }
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to remove from cart for user %d: %s", user_id, e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to remove from cart",
        )


@router.delete("/api/cart/{user_id}")
async def clear_cart(user_id: int):
    """Clear all items from cart."""
    if user_id <= 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid user ID",
        )
    
    try:
        success = await db.clear_cart(user_id)
        logger.info("Cart cleared for user %d", user_id)
        return {"status": "cleared"}
    except Exception as e:
        logger.error("Failed to clear cart for user %d: %s", user_id, e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to clear cart",
        )


# ── Warehouse Endpoints ──

@router.get("/api/warehouse")
async def get_warehouse():
    """Get all warehouse items with stock info."""
    try:
        items = await db.get_warehouse_items()
        stats = await db.get_warehouse_stats()
        return {"items": items, "stats": stats}
    except Exception as e:
        logger.error("Failed to get warehouse: %s", e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to fetch warehouse data",
        )


@router.get("/api/warehouse/transactions")
async def get_warehouse_transactions(limit: int = 50):
    """Get warehouse transaction history."""
    try:
        transactions = await db.get_warehouse_transactions(limit=limit)
        return transactions
    except Exception as e:
        logger.error("Failed to get warehouse transactions: %s", e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to fetch warehouse transactions",
        )


@router.get("/api/warehouse/stats")
async def get_warehouse_stats():
    """Get warehouse statistics."""
    try:
        stats = await db.get_warehouse_stats()
        return stats
    except Exception as e:
        logger.error("Failed to get warehouse stats: %s", e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to fetch warehouse stats",
        )


@router.get("/api/warehouse/stats/{period}")
async def get_warehouse_period_stats(period: str):
    """Get warehouse statistics for period (today, week, month, year, all)."""
    if period not in ("today", "week", "month", "year", "all"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid period. Use: today, week, month, year, all",
        )
    try:
        stats = await db.get_warehouse_dashboard_stats(period)
        return stats
    except Exception as e:
        logger.error("Failed to get warehouse period stats: %s", e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to fetch warehouse period stats",
        )


# ── Daily Sales Endpoints ──

class DailySaleRequest(BaseModel):
    total_amount: float = Field(gt=0)
    sale_date: str | None = None
    notes: str | None = None
    recorded_by: int


@router.get("/api/daily-sales")
async def get_daily_sales(limit: int = 50, offset: int = 0):
    """Get all daily sales records."""
    try:
        sales = await db.get_daily_sales(limit=limit, offset=offset)
        return sales
    except Exception as e:
        logger.error("Failed to get daily sales: %s", e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to fetch daily sales",
        )


@router.post("/api/daily-sales", response_model=dict)
async def create_daily_sale(data: DailySaleRequest):
    """Create a new daily sale record."""
    from datetime import date
    sale_date = data.sale_date or date.today().isoformat()
    try:
        sale_id = await db.create_daily_sale(
            total_amount=data.total_amount,
            sale_date=sale_date,
            notes=data.notes,
            recorded_by=data.recorded_by,
        )
        logger.info("Daily sale created: #%d, amount=%.2f", sale_id, data.total_amount)
        return {"id": sale_id, "status": "created"}
    except Exception as e:
        logger.error("Failed to create daily sale: %s", e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create daily sale",
        )


@router.delete("/api/daily-sales/{sale_id}")
async def delete_daily_sale(sale_id: int):
    """Delete a daily sale record."""
    if sale_id <= 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid sale ID",
        )
    try:
        success = await db.delete_daily_sale(sale_id)
        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Daily sale not found",
            )
        return {"status": "deleted"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to delete daily sale: %s", e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete daily sale",
        )


@router.get("/api/daily-sales/stats")
async def get_daily_sales_stats():
    """Get overall daily sales statistics."""
    try:
        stats = await db.get_daily_sales_stats("all")
        return stats
    except Exception as e:
        logger.error("Failed to get daily sales stats: %s", e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to fetch daily sales stats",
        )


@router.get("/api/daily-sales/stats/{period}")
async def get_daily_sales_period_stats(period: str):
    """Get daily sales statistics for period (today, week, month, year, all)."""
    if period not in ("today", "week", "month", "year", "all"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid period. Use: today, week, month, year, all",
        )
    try:
        stats = await db.get_daily_sales_stats(period)
        return stats
    except Exception as e:
        logger.error("Failed to get daily sales period stats: %s", e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to fetch daily sales period stats",
        )
