import asyncpg
from datetime import date

from bot.config import settings


class Database:
    def __init__(self):
        self.pool: asyncpg.Pool | None = None

    async def connect(self):
        if self.pool:
            return
        self.pool = await asyncpg.create_pool(settings.effective_database_url)

        async with self.pool.acquire() as conn:
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS categories (
                    id SERIAL PRIMARY KEY,
                    name VARCHAR(255) NOT NULL,
                    created_at TIMESTAMPTZ DEFAULT NOW()
                )
            """)

            await conn.execute("""
                CREATE TABLE IF NOT EXISTS products (
                    id SERIAL PRIMARY KEY,
                    category_id INTEGER REFERENCES categories(id) ON DELETE CASCADE,
                    name VARCHAR(255) NOT NULL,
                    description TEXT,
                    price NUMERIC(12, 2) NOT NULL,
                    image_url TEXT,
                    is_available BOOLEAN DEFAULT TRUE,
                    created_at TIMESTAMPTZ DEFAULT NOW()
                )
            """)

            await conn.execute("""
                CREATE TABLE IF NOT EXISTS orders (
                    id SERIAL PRIMARY KEY,
                    user_id BIGINT NOT NULL,
                    user_name VARCHAR(255),
                    phone VARCHAR(20),
                    address TEXT,
                    total_amount NUMERIC(12, 2) NOT NULL,
                    status VARCHAR(20) DEFAULT 'pending',
                    created_at TIMESTAMPTZ DEFAULT NOW()
                )
            """)

            await conn.execute("""
                CREATE TABLE IF NOT EXISTS order_items (
                    id SERIAL PRIMARY KEY,
                    order_id INTEGER REFERENCES orders(id) ON DELETE CASCADE,
                    product_id INTEGER REFERENCES products(id),
                    product_name VARCHAR(255) NOT NULL,
                    quantity INTEGER NOT NULL,
                    price NUMERIC(12, 2) NOT NULL
                )
            """)

            await conn.execute("""
                CREATE TABLE IF NOT EXISTS order_status_log (
                    id SERIAL PRIMARY KEY,
                    order_id INTEGER REFERENCES orders(id) ON DELETE CASCADE,
                    old_status VARCHAR(20),
                    new_status VARCHAR(20) NOT NULL,
                    changed_by BIGINT NOT NULL,
                    created_at TIMESTAMPTZ DEFAULT NOW()
                )
            """)

            await conn.execute("""
                CREATE TABLE IF NOT EXISTS carts (
                    id SERIAL PRIMARY KEY,
                    user_id BIGINT NOT NULL UNIQUE,
                    created_at TIMESTAMPTZ DEFAULT NOW(),
                    updated_at TIMESTAMPTZ DEFAULT NOW()
                )
            """)

            await conn.execute("""
                CREATE TABLE IF NOT EXISTS cart_items (
                    id SERIAL PRIMARY KEY,
                    cart_id INTEGER REFERENCES carts(id) ON DELETE CASCADE,
                    product_id INTEGER REFERENCES products(id) ON DELETE CASCADE,
                    quantity INTEGER NOT NULL,
                    added_at TIMESTAMPTZ DEFAULT NOW(),
                    UNIQUE(cart_id, product_id)
                )
            """)

            await conn.execute("""
                CREATE TABLE IF NOT EXISTS warehouse_items (
                    id SERIAL PRIMARY KEY,
                    product_id INTEGER REFERENCES products(id) ON DELETE CASCADE UNIQUE,
                    quantity NUMERIC(12, 2) NOT NULL DEFAULT 0,
                    min_quantity NUMERIC(12, 2) NOT NULL DEFAULT 0,
                    last_updated TIMESTAMPTZ DEFAULT NOW()
                )
            """)

            await conn.execute("""
                CREATE TABLE IF NOT EXISTS warehouse_transactions (
                    id SERIAL PRIMARY KEY,
                    product_id INTEGER REFERENCES products(id) ON DELETE CASCADE,
                    quantity_change NUMERIC(12, 2) NOT NULL,
                    transaction_type VARCHAR(20) NOT NULL,
                    notes TEXT,
                    created_by BIGINT NOT NULL,
                    created_at TIMESTAMPTZ DEFAULT NOW()
                )
            """)

            await conn.execute("""
                CREATE TABLE IF NOT EXISTS daily_sales (
                    id SERIAL PRIMARY KEY,
                    total_amount NUMERIC(12, 2) NOT NULL,
                    notes TEXT,
                    sale_date DATE NOT NULL DEFAULT CURRENT_DATE,
                    recorded_by BIGINT NOT NULL,
                    created_at TIMESTAMPTZ DEFAULT NOW()
                )
            """)

    async def close(self):
        if self.pool:
            await self.pool.close()

    # ── Categories ──

    async def get_categories(self) -> list[dict]:
        async with self.pool.acquire() as conn:
            rows = await conn.fetch("SELECT * FROM categories ORDER BY id")
            return [dict(r) for r in rows]

    async def get_category(self, category_id: int) -> dict | None:
        async with self.pool.acquire() as conn:
            row = await conn.fetchrow("SELECT * FROM categories WHERE id = $1", category_id)
            return dict(row) if row else None

    async def create_category(self, name: str) -> int:
        async with self.pool.acquire() as conn:
            return await conn.fetchval("INSERT INTO categories (name) VALUES ($1) RETURNING id", name)

    async def delete_category(self, category_id: int) -> bool:
        async with self.pool.acquire() as conn:
            result = await conn.execute("DELETE FROM categories WHERE id = $1", category_id)
            return int(result.split()[-1]) > 0

    # ── Products ──

    async def get_product(self, product_id: int) -> dict | None:
        async with self.pool.acquire() as conn:
            row = await conn.fetchrow("SELECT * FROM products WHERE id = $1", product_id)
            return dict(row) if row else None

    async def get_all_products(self) -> list[dict]:
        async with self.pool.acquire() as conn:
            rows = await conn.fetch(
                "SELECT * FROM products WHERE is_available = TRUE ORDER BY category_id, id"
            )
            return [dict(r) for r in rows]

    async def get_all_products_admin(self) -> list[dict]:
        async with self.pool.acquire() as conn:
            rows = await conn.fetch("SELECT * FROM products ORDER BY category_id, id")
            return [dict(r) for r in rows]

    async def get_products_by_category(self, category_id: int) -> list[dict]:
        async with self.pool.acquire() as conn:
            rows = await conn.fetch(
                "SELECT * FROM products WHERE category_id = $1 AND is_available = TRUE ORDER BY id",
                category_id,
            )
            return [dict(r) for r in rows]

    async def create_product(
        self, category_id: int, name: str, description: str | None,
        price: float, image_url: str | None
    ) -> int:
        async with self.pool.acquire() as conn:
            return await conn.fetchval(
                """
                INSERT INTO products (category_id, name, description, price, image_url)
                VALUES ($1, $2, $3, $4, $5) RETURNING id
                """,
                category_id, name, description, price, image_url,
            )

    async def update_product(
        self, product_id: int, **kwargs
    ) -> bool:
        allowed = {"name", "description", "price", "image_url", "is_available", "category_id"}
        updates = {k: v for k, v in kwargs.items() if k in allowed and v is not None}
        if not updates:
            return False
        set_clause = ", ".join(f"{k} = ${i+1}" for i, k in enumerate(updates))
        values = list(updates.values()) + [product_id]
        async with self.pool.acquire() as conn:
            result = await conn.execute(
                f"UPDATE products SET {set_clause} WHERE id = ${len(updates)+1}",
                *values,
            )
            return int(result.split()[-1]) > 0

    async def delete_product(self, product_id: int) -> bool:
        async with self.pool.acquire() as conn:
            result = await conn.execute("DELETE FROM products WHERE id = $1", product_id)
            return int(result.split()[-1]) > 0

    async def toggle_product_availability(self, product_id: int) -> bool | None:
        async with self.pool.acquire() as conn:
            row = await conn.fetchrow("SELECT is_available FROM products WHERE id = $1", product_id)
            if not row:
                return None
            new_val = not row["is_available"]
            await conn.execute(
                "UPDATE products SET is_available = $1 WHERE id = $2", new_val, product_id
            )
            return new_val

    # ── Orders ──

    async def create_order(
        self,
        user_id: int,
        user_name: str | None,
        phone: str,
        address: str,
        items: list[dict],
    ) -> int:
        async with self.pool.acquire() as conn:
            total = sum(item["price"] * item["quantity"] for item in items)
            order_id = await conn.fetchval(
                """
                INSERT INTO orders (user_id, user_name, phone, address, total_amount)
                VALUES ($1, $2, $3, $4, $5) RETURNING id
                """,
                user_id, user_name, phone, address, total,
            )
            for item in items:
                await conn.execute(
                    """
                    INSERT INTO order_items (order_id, product_id, product_name, quantity, price)
                    VALUES ($1, $2, $3, $4, $5)
                    """,
                    order_id, item["product_id"], item["name"], item["quantity"], item["price"],
                )
            return order_id

    async def get_order(self, order_id: int) -> dict | None:
        async with self.pool.acquire() as conn:
            row = await conn.fetchrow("SELECT * FROM orders WHERE id = $1", order_id)
            if not row:
                return None
            order = dict(row)
            items_rows = await conn.fetch(
                "SELECT * FROM order_items WHERE order_id = $1", order_id
            )
            order["items"] = [dict(r) for r in items_rows]
            return order

    async def get_orders(self, limit: int = 50, offset: int = 0, status: str | None = None) -> list[dict]:
        async with self.pool.acquire() as conn:
            if status:
                rows = await conn.fetch(
                    "SELECT * FROM orders WHERE status = $1 ORDER BY created_at DESC LIMIT $2 OFFSET $3",
                    status, limit, offset,
                )
            else:
                rows = await conn.fetch(
                    "SELECT * FROM orders ORDER BY created_at DESC LIMIT $1 OFFSET $2",
                    limit, offset,
                )
            return [dict(r) for r in rows]

    async def get_orders_by_user(self, user_id: int) -> list[dict]:
        async with self.pool.acquire() as conn:
            rows = await conn.fetch(
                "SELECT * FROM orders WHERE user_id = $1 ORDER BY created_at DESC",
                user_id,
            )
            return [dict(r) for r in rows]

    async def update_order_status(self, order_id: int, new_status: str, changed_by: int) -> bool:
        async with self.pool.acquire() as conn:
            row = await conn.fetchrow("SELECT status FROM orders WHERE id = $1", order_id)
            if not row:
                return False
            old_status = row["status"]
            await conn.execute(
                "UPDATE orders SET status = $1 WHERE id = $2", new_status, order_id
            )
            await conn.execute(
                """
                INSERT INTO order_status_log (order_id, old_status, new_status, changed_by)
                VALUES ($1, $2, $3, $4)
                """,
                order_id, old_status, new_status, changed_by,
            )
            return True

    # ── Stats ──

    async def get_stats(self) -> dict:
        async with self.pool.acquire() as conn:
            total_products = await conn.fetchval("SELECT COUNT(*) FROM products")
            total_categories = await conn.fetchval("SELECT COUNT(*) FROM categories")
            total_orders = await conn.fetchval("SELECT COUNT(*) FROM orders")
            total_revenue = await conn.fetchval("SELECT COALESCE(SUM(total_amount), 0) FROM orders WHERE status != 'cancelled'")
            pending_orders = await conn.fetchval("SELECT COUNT(*) FROM orders WHERE status = 'pending'")
            return {
                "total_products": total_products,
                "total_categories": total_categories,
                "total_orders": total_orders,
                "total_revenue": float(total_revenue),
                "pending_orders": pending_orders,
            }

    # ── Users who have ordered (for broadcast) ──

    async def get_dashboard_stats(self, period: str = "all") -> dict:
        period_conditions = {
            "today": "AND created_at >= CURRENT_DATE",
            "week": "AND created_at >= date_trunc('week', CURRENT_DATE)",
            "month": "AND created_at >= date_trunc('month', CURRENT_DATE)",
            "year": "AND created_at >= date_trunc('year', CURRENT_DATE)",
            "all": "",
        }
        date_filter = period_conditions.get(period, "")

        async with self.pool.acquire() as conn:
            total_orders = await conn.fetchval(
                f"SELECT COUNT(*) FROM orders WHERE 1=1 {date_filter}"
            )
            accepted_orders = await conn.fetchval(
                f"SELECT COUNT(*) FROM orders WHERE status = 'delivered' {date_filter}"
            )
            rejected_orders = await conn.fetchval(
                f"SELECT COUNT(*) FROM orders WHERE status = 'cancelled' {date_filter}"
            )
            pending_orders = await conn.fetchval(
                f"SELECT COUNT(*) FROM orders WHERE status = 'pending' {date_filter}"
            )
            total_revenue = await conn.fetchval(
                f"SELECT COALESCE(SUM(total_amount), 0) FROM orders WHERE status = 'delivered' {date_filter}"
            )

            period_labels = {
                "today": "Bugun",
                "week": "Bu hafta",
                "month": "Bu oy",
                "year": "Bu yil",
                "all": "Umumiy",
            }

            return {
                "period": period_labels.get(period, "Umumiy"),
                "total_orders": total_orders,
                "accepted_orders": accepted_orders,
                "rejected_orders": rejected_orders,
                "pending_orders": pending_orders,
                "total_revenue": float(total_revenue),
            }

    async def get_monthly_earnings(self, limit: int = 6) -> list[dict]:
        async with self.pool.acquire() as conn:
            rows = await conn.fetch(
                """
                SELECT
                    date_trunc('month', created_at) as month,
                    COUNT(*) as total_orders,
                    COUNT(*) FILTER (WHERE status = 'delivered') as accepted_orders,
                    COUNT(*) FILTER (WHERE status = 'cancelled') as rejected_orders,
                    COALESCE(SUM(total_amount) FILTER (WHERE status = 'delivered'), 0) as revenue
                FROM orders
                GROUP BY month
                ORDER BY month DESC
                LIMIT $1
                """,
                limit,
            )
            return [
                {
                    "month": r["month"],
                    "total_orders": r["total_orders"],
                    "accepted_orders": r["accepted_orders"],
                    "rejected_orders": r["rejected_orders"],
                    "revenue": float(r["revenue"]),
                }
                for r in rows
            ]

    async def get_unique_user_ids(self) -> list[int]:
        async with self.pool.acquire() as conn:
            rows = await conn.fetch("SELECT DISTINCT user_id FROM orders")
            return [r["user_id"] for r in rows]

    # ── Search ──

    async def search_products(self, query: str) -> list[dict]:
        async with self.pool.acquire() as conn:
            rows = await conn.fetch(
                """
                SELECT * FROM products
                WHERE is_available = TRUE AND (name ILIKE $1 OR description ILIKE $1)
                ORDER BY id
                """,
                f"%{query}%",
            )
            return [dict(r) for r in rows]

    # ── Cart ──

    async def get_or_create_cart(self, user_id: int) -> int:
        """Get existing cart or create new one. Returns cart_id."""
        async with self.pool.acquire() as conn:
            cart_id = await conn.fetchval("SELECT id FROM carts WHERE user_id = $1", user_id)
            if cart_id:
                return cart_id
            return await conn.fetchval(
                "INSERT INTO carts (user_id) VALUES ($1) RETURNING id", user_id
            )

    async def add_to_cart(self, user_id: int, product_id: int, quantity: int) -> bool:
        """Add or update item in cart. Returns success status."""
        if quantity <= 0:
            return False
        
        try:
            async with self.pool.acquire() as conn:
                cart_id = await self.get_or_create_cart(user_id)
                
                # Check if product exists and is available
                product = await conn.fetchrow(
                    "SELECT id FROM products WHERE id = $1 AND is_available = TRUE", product_id
                )
                if not product:
                    return False
                
                # Add or update cart item
                await conn.execute(
                    """
                    INSERT INTO cart_items (cart_id, product_id, quantity)
                    VALUES ($1, $2, $3)
                    ON CONFLICT (cart_id, product_id)
                    DO UPDATE SET quantity = quantity + $3
                    """,
                    cart_id, product_id, quantity,
                )
                
                # Update cart timestamp
                await conn.execute(
                    "UPDATE carts SET updated_at = NOW() WHERE id = $1", cart_id
                )
                return True
        except Exception:
            return False

    async def get_cart_items(self, user_id: int) -> list[dict]:
        """Get all items in user's cart with product details."""
        async with self.pool.acquire() as conn:
            rows = await conn.fetch(
                """
                SELECT 
                    ci.id, ci.product_id, ci.quantity,
                    p.name, p.price, p.image_url
                FROM cart_items ci
                JOIN carts c ON ci.cart_id = c.id
                JOIN products p ON ci.product_id = p.id
                WHERE c.user_id = $1
                ORDER BY ci.added_at
                """,
                user_id,
            )
            return [dict(r) for r in rows]

    async def remove_from_cart(self, user_id: int, product_id: int) -> bool:
        """Remove item from cart."""
        async with self.pool.acquire() as conn:
            result = await conn.execute(
                """
                DELETE FROM cart_items
                WHERE product_id = $1 AND cart_id = (
                    SELECT id FROM carts WHERE user_id = $2
                )
                """,
                product_id, user_id,
            )
            return int(result.split()[-1]) > 0

    async def clear_cart(self, user_id: int) -> bool:
        """Clear all items from user's cart."""
        async with self.pool.acquire() as conn:
            result = await conn.execute(
                """
                DELETE FROM cart_items
                WHERE cart_id = (SELECT id FROM carts WHERE user_id = $1)
                """,
                user_id,
            )
            return int(result.split()[-1]) > 0

    async def get_cart_total(self, user_id: int) -> dict:
        """Get cart total amount and item count."""
        async with self.pool.acquire() as conn:
            row = await conn.fetchrow(
                """
                SELECT 
                    COUNT(ci.id) as item_count,
                    COALESCE(SUM(ci.quantity * p.price), 0) as total_amount
                FROM cart_items ci
                JOIN carts c ON ci.cart_id = c.id
                JOIN products p ON ci.product_id = p.id
                WHERE c.user_id = $1
                """,
                user_id,
            )
            return {
                "item_count": row["item_count"] if row else 0,
                "total_amount": float(row["total_amount"]) if row else 0.0,
            }


    # ── Warehouse ──

    async def get_warehouse_items(self) -> list[dict]:
        async with self.pool.acquire() as conn:
            rows = await conn.fetch("""
                SELECT wi.id, wi.product_id, wi.quantity, wi.min_quantity, wi.last_updated,
                       p.name as product_name, p.price
                FROM warehouse_items wi
                JOIN products p ON wi.product_id = p.id
                ORDER BY p.name
            """)
            return [dict(r) for r in rows]

    async def get_warehouse_item(self, product_id: int) -> dict | None:
        async with self.pool.acquire() as conn:
            row = await conn.fetchrow("""
                SELECT wi.id, wi.product_id, wi.quantity, wi.min_quantity, wi.last_updated,
                       p.name as product_name, p.price
                FROM warehouse_items wi
                JOIN products p ON wi.product_id = p.id
                WHERE wi.product_id = $1
            """, product_id)
            return dict(row) if row else None

    async def init_warehouse_item(self, product_id: int, quantity: float = 0, min_quantity: float = 0) -> bool:
        async with self.pool.acquire() as conn:
            try:
                await conn.execute("""
                    INSERT INTO warehouse_items (product_id, quantity, min_quantity)
                    VALUES ($1, $2, $3)
                    ON CONFLICT (product_id)
                    DO UPDATE SET quantity = $2, min_quantity = $3, last_updated = NOW()
                """, product_id, quantity, min_quantity)
                return True
            except Exception:
                return False

    async def add_warehouse_stock(self, product_id: int, quantity: float, notes: str | None, created_by: int) -> bool:
        if quantity <= 0:
            return False
        async with self.pool.acquire() as conn:
            try:
                await conn.execute("""
                    INSERT INTO warehouse_items (product_id, quantity)
                    VALUES ($1, $2)
                    ON CONFLICT (product_id)
                    DO UPDATE SET quantity = warehouse_items.quantity + $2, last_updated = NOW()
                """, product_id, quantity)
                await conn.execute("""
                    INSERT INTO warehouse_transactions (product_id, quantity_change, transaction_type, notes, created_by)
                    VALUES ($1, $2, 'in', $3, $4)
                """, product_id, quantity, notes, created_by)
                return True
            except Exception:
                return False

    async def remove_warehouse_stock(self, product_id: int, quantity: float, notes: str | None, created_by: int) -> bool:
        if quantity <= 0:
            return False
        async with self.pool.acquire() as conn:
            try:
                row = await conn.fetchrow(
                    "SELECT quantity FROM warehouse_items WHERE product_id = $1", product_id
                )
                if not row or row["quantity"] < quantity:
                    return False
                await conn.execute(
                    "UPDATE warehouse_items SET quantity = quantity - $1, last_updated = NOW() WHERE product_id = $2",
                    quantity, product_id,
                )
                await conn.execute("""
                    INSERT INTO warehouse_transactions (product_id, quantity_change, transaction_type, notes, created_by)
                    VALUES ($1, $2, 'out', $3, $4)
                """, product_id, -quantity, notes, created_by)
                return True
            except Exception:
                return False

    async def get_warehouse_transactions(self, product_id: int | None = None, limit: int = 50) -> list[dict]:
        async with self.pool.acquire() as conn:
            if product_id:
                rows = await conn.fetch("""
                    SELECT wt.*, p.name as product_name
                    FROM warehouse_transactions wt
                    JOIN products p ON wt.product_id = p.id
                    WHERE wt.product_id = $1
                    ORDER BY wt.created_at DESC LIMIT $2
                """, product_id, limit)
            else:
                rows = await conn.fetch("""
                    SELECT wt.*, p.name as product_name
                    FROM warehouse_transactions wt
                    JOIN products p ON wt.product_id = p.id
                    ORDER BY wt.created_at DESC LIMIT $1
                """, limit)
            return [dict(r) for r in rows]

    async def get_warehouse_stats(self) -> dict:
        async with self.pool.acquire() as conn:
            total_items = await conn.fetchval("SELECT COUNT(*) FROM warehouse_items")
            total_stock = await conn.fetchval(
                "SELECT COALESCE(SUM(wi.quantity), 0) FROM warehouse_items wi"
            )
            total_value = await conn.fetchval("""
                SELECT COALESCE(SUM(wi.quantity * p.price), 0)
                FROM warehouse_items wi
                JOIN products p ON wi.product_id = p.id
            """)
            low_stock = await conn.fetchval("""
                SELECT COUNT(*) FROM warehouse_items
                WHERE quantity <= min_quantity
            """)
            return {
                "total_items": total_items,
                "total_stock_quantity": float(total_stock),
                "total_stock_value": float(total_value),
                "low_stock_items": low_stock,
            }

    async def get_warehouse_dashboard_stats(self, period: str = "all") -> dict:
        date_filter = {
            "today": "AND wt.created_at >= CURRENT_DATE",
            "week": "AND wt.created_at >= date_trunc('week', CURRENT_DATE)",
            "month": "AND wt.created_at >= date_trunc('month', CURRENT_DATE)",
            "year": "AND wt.created_at >= date_trunc('year', CURRENT_DATE)",
            "all": "",
        }.get(period, "")

        async with self.pool.acquire() as conn:
            stock_in = await conn.fetchval(
                f"SELECT COALESCE(SUM(quantity_change), 0) FROM warehouse_transactions wt WHERE quantity_change > 0 {date_filter}"
            )
            stock_out = await conn.fetchval(
                f"SELECT COALESCE(SUM(quantity_change), 0) FROM warehouse_transactions wt WHERE quantity_change < 0 {date_filter}"
            )
            transactions = await conn.fetchval(
                f"SELECT COUNT(*) FROM warehouse_transactions wt WHERE 1=1 {date_filter}"
            )
            return {
                "stock_in": float(stock_in or 0),
                "stock_out": float(abs(stock_out or 0)),
                "transactions": transactions or 0,
            }

    # ── Daily Sales ──

    async def create_daily_sale(self, total_amount: float, sale_date: str | date, notes: str | None, recorded_by: int) -> int:
        if isinstance(sale_date, str):
            from datetime import datetime
            sale_date = datetime.strptime(sale_date, "%Y-%m-%d").date()
        async with self.pool.acquire() as conn:
            return await conn.fetchval(
                "INSERT INTO daily_sales (total_amount, sale_date, notes, recorded_by) VALUES ($1, $2, $3, $4) RETURNING id",
                total_amount, sale_date, notes, recorded_by,
            )

    async def get_daily_sales(self, limit: int = 50, offset: int = 0) -> list[dict]:
        async with self.pool.acquire() as conn:
            rows = await conn.fetch(
                "SELECT * FROM daily_sales ORDER BY sale_date DESC, created_at DESC LIMIT $1 OFFSET $2",
                limit, offset,
            )
            return [dict(r) for r in rows]

    async def get_daily_sale(self, sale_id: int) -> dict | None:
        async with self.pool.acquire() as conn:
            row = await conn.fetchrow("SELECT * FROM daily_sales WHERE id = $1", sale_id)
            return dict(row) if row else None

    async def delete_daily_sale(self, sale_id: int) -> bool:
        async with self.pool.acquire() as conn:
            result = await conn.execute("DELETE FROM daily_sales WHERE id = $1", sale_id)
            return int(result.split()[-1]) > 0

    async def get_daily_sales_stats(self, period: str = "all") -> dict:
        date_filter = {
            "today": "AND sale_date = CURRENT_DATE",
            "week": "AND sale_date >= date_trunc('week', CURRENT_DATE)",
            "month": "AND sale_date >= date_trunc('month', CURRENT_DATE)",
            "year": "AND sale_date >= date_trunc('year', CURRENT_DATE)",
            "all": "",
        }.get(period, "")

        period_labels = {
            "today": "Bugun",
            "week": "Bu hafta",
            "month": "Bu oy",
            "year": "Bu yil",
            "all": "Umumiy",
        }

        async with self.pool.acquire() as conn:
            total_sales = await conn.fetchval(
                f"SELECT COUNT(*) FROM daily_sales WHERE 1=1 {date_filter}"
            )
            total_amount = await conn.fetchval(
                f"SELECT COALESCE(SUM(total_amount), 0) FROM daily_sales WHERE 1=1 {date_filter}"
            )
            avg_sale = await conn.fetchval(
                f"SELECT COALESCE(AVG(total_amount), 0) FROM daily_sales WHERE 1=1 {date_filter}"
            )
            return {
                "period": period_labels.get(period, "Umumiy"),
                "total_sales": total_sales,
                "total_amount": float(total_amount),
                "average_sale": float(avg_sale),
            }

    async def get_monthly_daily_sales(self, limit: int = 6) -> list[dict]:
        async with self.pool.acquire() as conn:
            rows = await conn.fetch("""
                SELECT
                    date_trunc('month', sale_date) as month,
                    COUNT(*) as total_sales,
                    COALESCE(SUM(total_amount), 0) as revenue
                FROM daily_sales
                GROUP BY month
                ORDER BY month DESC
                LIMIT $1
            """, limit)
            return [
                {
                    "month": r["month"],
                    "total_sales": r["total_sales"],
                    "revenue": float(r["revenue"]),
                }
                for r in rows
            ]


db = Database()
