from aiogram import Router, types
from aiogram.filters import Command

from bot.services.database import db

router = Router()

STATUS_EMOJI = {
    "pending": "⏳ Kutilmoqda",
    "processing": "👨‍🍳 Tayyorlanmoqda",
    "delivered": "✅ Yetkazilgan",
    "cancelled": "❌ Bekor qilingan",
}


@router.message(Command("myorders"))
async def my_orders(message: types.Message):
    user_id = message.from_user.id
    orders = await db.get_orders_by_user(user_id)
    if not orders:
        await message.answer("Sizning hali buyurtmalaringiz yo'q.")
        return
    for order in orders[:5]:
        items_rows = await db.get_order(order["id"])
        items = items_rows["items"] if items_rows else []
        items_text = "\n".join(
            f"  • {i['product_name']} × {i['quantity']} = {i['price'] * i['quantity']:,.0f} so'm"
            for i in items
        )
        status_text = STATUS_EMOJI.get(order["status"], order["status"])
        text = (
            f"📦 <b>Buyurtma #{order['id']}</b>\n"
            f"{items_text}\n"
            f"💰 Jami: {order['total_amount']:,.0f} so'm\n"
            f"📅 {order['created_at'].strftime('%d.%m.%Y %H:%M') if order.get('created_at') else '—'}\n"
            f"{status_text}"
        )
        await message.answer(text, parse_mode="HTML")
    if len(orders) > 5:
        await message.answer(f"Yana {len(orders) - 5} ta buyurtma bor. Batafsil uchun webapp orqali ko'ring.")


@router.message(Command("contact"))
async def contact(message: types.Message):
    await message.answer(
        "📞 Bog'lanish: +998 XX XXX XX XX\n"
        "📩 Telegram: @admin\n"
        "Savol va takliflar uchun murojaat qiling."
    )
