# Architecture Guide

## Loyiha Arxitekturasi

### Asosiy Tamoyillar

1. **Layered Architecture** - Qoliplar (presentasion), xizmatlar (service), va ma'lumotlar (data) qoliplarini ajratish
2. **Async-First** - Barcha I/O operatsiyalari asinxron
3. **Clean Code** - Type hints, dokumentatsiya, va eng yaxshi amaliyotlar
4. **Separation of Concerns** - Har bir modul o'z mas'uliyatiga ega

## Komponentlar

### Bot Qolpi (Presentation Layer)

**Fayl**: `bot/handlers/*.py`

Telegram bilan o'zaro ta'sir qiladi. Foydalanuvchi xabarlari qabul qiladi va javob beradi.

```
┌─────────────────────┐
│   Telegram Users    │
└──────────┬──────────┘
           │
      Handlers:
      ├── start.py      → Foydalanuvchi komanda
      ├── admin.py      → Admin komanda
      └── user.py       → Foydalanuvchi komanda
           │
           ▼
     ┌─────────────┐
     │  Database   │
     └─────────────┘
```

### Web API Qolpi

**Fayl**: `web/routes.py`

RESTful API taqdim etadi. HTTP so'rovlarni qayta ishlaydi.

```
┌──────────────┐
│  Web Client  │
└──────┬───────┘
       │
    Routes:
    ├── /api/categories
    ├── /api/products
    ├── /api/orders
    ├── /api/cart
    │
    ▼
   Database
```

### Service Layer

**Fayl**: `bot/services/database.py`, `bot/services/notifier.py`

Asosiy biznes logikasi bu yerda yashaydi. Database va tashqi xizmatlar bilan aloqa.

```
Database Class:
├── Categories CRUD
├── Products CRUD
├── Orders CRUD
├── Cart CRUD
└── Stats

Notifier Class:
├── Order notifications
└── Channel integration
```

### Utilities Layer

**Fayl**: `bot/utils/*.py`

Qayta ishlatish mumkin bo'lgan funksiyalar.

```
validators.py   → Input validatsiya
logger.py       → Logging utilities
```

### Configuration Layer

**Fayl**: `bot/config.py`, `.env`

Aqlli sozlama. Hech qanday hard-coded qiymat yo'q.

```
Environment Variables:
├── BOT_TOKEN
├── CHANNEL_ID
├── DATABASE_URL
├── ADMIN_IDS
└── JWT_SECRET_KEY
```

## Data Flow

### Buyurtma Yaratish Oqimi

```
1. Foydalanuvchi /start -> Tugmani bosadi
   │
2. Button click -> Web app yoki API
   │
3. POST /api/orders
   │
4. Validation
   ├── ✓ Phone valid?
   ├── ✓ Address valid?
   └── ✓ Items valid?
   │
5. Database save
   ├── Create order record
   └── Create order_items records
   │
6. Post-creation actions
   ├── Notify channel
   ├── Log action
   └── Return order_id
```

### Cart Management Oqimi

```
1. User adds to cart
   POST /api/cart/{user_id}
   │
2. Validation
   ├── ✓ Product exists?
   ├── ✓ Quantity valid?
   └── ✓ Product available?
   │
3. Database operations
   ├── Create/update cart record
   └── Create/update cart_items
   │
4. Return updated cart totals
```

## Database Schema

```
categories
├── id (PK)
├── name
└── created_at

products
├── id (PK)
├── category_id (FK)
├── name
├── description
├── price
├── image_url
├── is_available
└── created_at

orders
├── id (PK)
├── user_id
├── user_name
├── phone
├── address
├── total_amount
├── status
└── created_at

order_items
├── id (PK)
├── order_id (FK)
├── product_id (FK)
├── product_name
├── quantity
└── price

order_status_log
├── id (PK)
├── order_id (FK)
├── old_status
├── new_status
├── changed_by
└── created_at

carts
├── id (PK)
├── user_id (UNIQUE)
├── created_at
└── updated_at

cart_items
├── id (PK)
├── cart_id (FK)
├── product_id (FK)
├── quantity
├── added_at
└── UNIQUE(cart_id, product_id)
```

## Error Handling Strategy

### Try-Catch Pattern

```python
try:
    # Asosiy logika
    result = await db.create_order(...)
except ValidationError as e:
    logger.error("Validation failed: %s", e)
    raise HTTPException(status_code=400, detail=str(e))
except DatabaseError as e:
    logger.error("Database error: %s", e)
    raise HTTPException(status_code=500, detail="Internal server error")
```

### Logging Levels

- `INFO`: Muhim voqealar (order created, user action)
- `WARNING`: Ehtiyotlik (retries, missing data)
- `ERROR`: Xatoliklar (exceptions, failed operations)

## Performance Considerations

1. **Database Connection Pool** - AsyncPG pool reuse
2. **Async Operations** - Hech qanday blocking I/O
3. **Validation Early** - Xatolarni tez aniqlash
4. **Efficient Queries** - `JOIN` bilan bitta query

## Security

1. **Input Validation** - Barcha input qat'iy tekshiriladi
2. **SQL Injection Protection** - Parameterized queries (asyncpg handles this)
3. **Admin Check** - Har bir admin uchun middleware
4. **JWT Tokens** - API autentifikatsiyasi uchun
5. **CORS** - Cross-origin requests haqqida ehtiyotlik

## Testing Strategy

### Unit Tests
- Database methods
- Validators
- Utilities

### Integration Tests
- API endpoints
- Bot handlers
- Database operations

### E2E Tests (Manual)
- Buyurtma yaratish to'liq oqimi
- Cart workflow

## Kengaytirish Nuqtalari

1. **New Handlers** - `bot/handlers/new_feature.py` qo'shish
2. **New API Routes** - `web/routes.py` ga endpoint qo'shish
3. **New Services** - `bot/services/new_service.py` yaratish
4. **New Validators** - `bot/utils/validators.py` ga qo'shish

## Deployment

```
Development → Testing → Staging → Production

docker-compose.yml handles:
├── PostgreSQL database
├── Bot service
└── Web API service
```
