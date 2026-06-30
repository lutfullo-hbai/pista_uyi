# Pista Uyi - E-commerce Telegram Bot + Web API

Telegram bot va FastAPI orqali e-commerce platformasi. Foydalanuvchilar Telegram orqali buyurtma beradilar, adminlar webdan yoki botdan boshqaradilar.

## 🚀 Xususiyatlar

- **Telegram Bot**: Buyurtma qilish, categoriyalar, mahsulotlar
- **Web API**: RESTful API barcha operatsiyalar uchun
- **Savatcha Tizimi**: Mahsulotlarni savatga qo'shish, miqdor o'zgartirish
- **Admin Panel**: Mahsulot va kategoriya boshqaruvi
- **PostgreSQL**: Asosiy ma'lumotlar bazasi
- **Async/Await**: Tezkor va samarali

## 📋 Loyiha Struktura

```
bot/
  ├── handlers/          # Telegram handler'lar
  │   ├── start.py      # /start va foydalanuvchi komanda
  │   ├── admin.py      # Admin komanda va CRUD
  │   └── user.py       # Foydalanuvchi komanda
  ├── services/         # Xizmatlar
  │   ├── database.py   # Ma'lumotlar bazasi CRUD
  │   └── notifier.py   # Kanalni xabardor qilish
  ├── utils/            # Yordamchi funksiyalar
  │   ├── validators.py # Input validatsiya
  │   └── logger.py     # Logging
  ├── keyboards/        # Telegram tugmalari
  ├── config.py         # Konfiguratsiya
  └── bot.py           # Bot asosi

web/
  ├── routes.py         # API endpointlari
  ├── security.py       # JWT autentifikatsiya
  ├── server.py         # FastAPI app
  └── static/          # Frontend faillar

tests/                  # Unit testlar
```

## 🔧 O'rnatish

### Talablar
- Python 3.12+
- PostgreSQL 12+
- Docker (ixtiyoriy)

### Lokal O'rnatish

1. **Repository klonlash**
```bash
git clone <repo>
cd pista_uyi
```

2. **Virtual Environment yaratish**
```bash
python -m venv .venv
source .venv/bin/activate  # Linux/Mac
# yoki
.venv\Scripts\activate     # Windows
```

3. **Paketlarni o'rnatish**
```bash
pip install -r requirements.txt
```

4. **.env fayl yaratish**
```env
BOT_TOKEN=your_bot_token_here
CHANNEL_ID=@your_channel_name  # yoki -100123456789
DATABASE_URL=postgresql://user:password@localhost:5432/pista_uyi
WEB_APP_URL=http://localhost:3000
ADMIN_IDS=[123456789, 987654321]
JWT_SECRET_KEY=your-secret-key-here
```

5. **Bazani o'rnatish**
```bash
# Dastur avtomatik jadvallarni yaratadi
python run.py --web-only
```

### Docker orqali

```bash
docker-compose up -d
```

## 🎯 API Endpointlari

### Kategoriya va Mahsulotlar

```
GET  /api/categories          # Barcha kategoriyalar
GET  /api/products            # Barcha mahsulotlar
GET  /api/products/{cat_id}   # Kategoriya bo'yicha mahsulotlar
```

### Buyurtmalar

```
GET  /api/orders/user/{user_id}        # Foydalanuvchi buyurtmalari
POST /api/orders                        # Yangi buyurtma yaratish
```

**Buyurtma yaratish:**
```json
POST /api/orders
{
  "user_id": 123456789,
  "user_name": "Abubakr",
  "phone": "+998901234567",
  "address": "Tashkent, Mirza Ulug'bek ko'chasi",
  "items": [
    {
      "product_id": 1,
      "name": "Pista",
      "quantity": 2,
      "price": 15000
    }
  ]
}
```

### Savatcha (Cart)

```
GET    /api/cart/{user_id}                    # Savatcha ko'rish
POST   /api/cart/{user_id}                    # Mahsulot qo'shish
DELETE /api/cart/{user_id}/{product_id}      # Mahsulot o'chirish
DELETE /api/cart/{user_id}                    # Savatcha to'liq o'chirish
```

**Savatcha qo'shish:**
```json
POST /api/cart/123456789
{
  "product_id": 1,
  "quantity": 2
}
```

## 🤖 Telegram Bot Komanda

### Foydalanuvchi

```
/start              # Bosh menu
/myorders           # Mening buyurtmalarim
/contact            # Bog'lanish ma'lumotlari
```

### Admin

```
/admin              # Admin panel
/add_category       # Kategoriya qo'shish
/add_product        # Mahsulot qo'shish
/products           # Mahsulotlar ro'yxati
/toggle_product     # Mahsulotni aktiv/passiv qilish
/orders             # Barcha buyurtmalar
/status             # Buyurtma statusini o'zgartirish
```

## 🏃 Ishga Tushirish

### Faqat Bot
```bash
python run.py --bot-only
```

### Faqat Web Server
```bash
python run.py --web-only
```

### Ikkalasini Birga
```bash
python run.py
```

## 🧪 Testlar

```bash
# Barcha testlarni ishga tushirish
pytest

# Faqat muayyan faylni
pytest tests/test_routes.py

# Coverage bilan
pytest --cov=bot --cov=web
```

## 📊 Database Schema

### Jadvallar

- **categories** - Mahsulot kategoriyalari
- **products** - Mahsulotlar
- **orders** - Buyurtmalar
- **order_items** - Buyurtma mahsulotlari
- **order_status_log** - Buyurtma status o'zgarishlari
- **carts** - Foydalanuvchi savatchalari
- **cart_items** - Savatcha mahsulotlari

## 🔒 Xavfsizlik

- JWT tokenlar API autentifikatsiyasi uchun
- Admin tekshirish Telegram bot uchun
- Validatsiya va sanitizatsiya
- CORS konfiguratsiyasi

## 🐛 Debuging

### Logging

Logging avtomatik sozlangan. Fayllari `/logs` papkasida saqlanadi:

```python
from bot.utils.logger import get_logger

logger = get_logger(__name__)
logger.info("Message")
logger.error("Error occurred")
```

### Xatoliklarni Tekshirish

```bash
# Konteynerda
docker-compose logs -f

# Lokal
python run.py  # Bu barcha loglarni ko'rsatadi
```

## 📝 Konfiguratsiya

### Environment O'zgaruvchilari

| O'zgaruvchi | Tavsif | Misol |
|-----------|--------|-------|
| `BOT_TOKEN` | Telegram bot token | `123:ABC` |
| `CHANNEL_ID` | Xabar yuborish kanali | `@news_channel` yoki `-100123` |
| `DATABASE_URL` | PostgreSQL ulanish | `postgresql://user:pass@localhost/db` |
| `WEB_APP_URL` | Web app URL | `http://localhost:3000` |
| `ADMIN_IDS` | Admin user ID'lari | `[123456, 789012]` |
| `JWT_SECRET_KEY` | JWT imzolash kaliti | `your-secret-key` |

## 🚀 Production Deploy

### Docker Compose

```bash
docker-compose -f docker-compose.yml up -d
```

### Environment

1. `.env` faylni real qiymatlari bilan to'ldirish
2. `JWT_SECRET_KEY` o'zgartirish
3. HTTPS sozlashtirish
4. Database backup tizimini o'rnatish

## 📚 Qo'shimcha

### Clean Code Tamoyillari

- **Modulalash**: Har bir xizmat o'z fayl va mas'uliyatga ega
- **Validatsiya**: Barcha input validatsiyasi qilinadi
- **Error Handling**: Barcha xatoliklarni to'liq qayta ishlash
- **Logging**: Barcha muhim voqealarni log qilish
- **Type Hints**: Python type hints ishlatiladi
- **Documentation**: Docstring'lar barcha funksiyalarda

### Kengaytirish Imkoniyatlari

1. **Toʻlov Integratsiyasi**: Click, Payme, Stripe qo'shish
2. **Email Notifikatsiya**: Buyurtma tasdiqlamasini email orqali
3. **Foydalanuvchi Profili**: Profilni o'zgartirish, raqamni o'zgartirish
4. **Search**: Mahsulotlar bo'yicha qidirish
5. **Reviews**: Foydalanuvchi sharhlar
6. **Analytics**: Sotish statistikasi va raporti

## 📞 Support

Muammolar uchun GitHub issues ochish yoki `@admin` ga Telegram orqali xabar berishingiz mumkin.

## 📄 Litsenziya

MIT License

