from aiogram import Router, types, F
from aiogram.filters import Command
from aiogram.utils.keyboard import InlineKeyboardBuilder

from bot.keyboards.reply import main_keyboard, admin_keyboard
from bot.config import settings
from bot.services.database import db

router = Router()

STATUS_EMOJI = {
    "pending": "⏳ Kutilmoqda",
    "processing": "👨‍🍳 Tayyorlanmoqda",
    "delivered": "✅ Yetkazilgan",
    "cancelled": "❌ Bekor qilingan",
}


def is_admin(user_id: int) -> bool:
    return user_id in settings.admin_ids


@router.message(Command("chatid"))
async def chat_id_handler(message: types.Message):
    await message.answer(
        f"Chat ID: <code>{message.chat.id}</code>\n"
        f"Chat turi: {message.chat.type}\n"
        f"Chat nomi: {message.chat.title or message.chat.first_name or ''}",
        parse_mode="HTML",
    )


@router.message(Command("start"))
async def start_handler(message: types.Message):
    keyboard = admin_keyboard() if is_admin(message.from_user.id) else main_keyboard()
    await message.answer(
        "Assalomu alaykum! Pista Uyi botiga xush kelibsiz.\n\n"
        "Pastdagi tugma orqali magazinga kirishingiz mumkin.",
        reply_markup=keyboard,
    )


@router.message(F.text == "📋 Mening buyurtmalarim")
async def my_orders_button(message: types.Message):
    user_id = message.from_user.id
    orders = await db.get_orders_by_user(user_id)
    if not orders:
        await message.answer("Sizning hali buyurtmalaringiz yo'q.")
        return
    for order in orders[:5]:
        order_full = await db.get_order(order["id"])
        items = order_full["items"] if order_full else []
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
        await message.answer(f"Yana {len(orders) - 5} ta buyurtma bor.")


@router.message(F.text == "📞 Bog'lanish")
async def contact_button(message: types.Message):
    await message.answer(
        "📞 Bog'lanish: +998 001 26 62\n"
        "📩 Telegram: @lutfulloai\n\n"
        "Savol va takliflar uchun murojaat qilishingiz mumkin ."
    )


def dashboard_period_keyboard(prefix: str = "dash") -> InlineKeyboardBuilder:
    builder = InlineKeyboardBuilder()
    builder.button(text="📅 Bugun", callback_data=f"{prefix}:today")
    builder.button(text="📅 Bu hafta", callback_data=f"{prefix}:week")
    builder.button(text="📅 Bu oy", callback_data=f"{prefix}:month")
    builder.button(text="📅 Bu yil", callback_data=f"{prefix}:year")
    builder.button(text="📅 Umumiy", callback_data=f"{prefix}:all")
    builder.adjust(3, 2)
    return builder.as_markup()


def dashboard_switch_keyboard() -> types.InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="🛒 Market", callback_data="dash_switch:market")
    builder.button(text="📦 Ombor", callback_data="dash_switch:warehouse")
    builder.button(text="💰 Tushum", callback_data="dash_switch:dailysales")
    builder.adjust(3)
    return builder.as_markup()


async def _combine_keyboards(period_prefix: str) -> types.InlineKeyboardMarkup:
    period_kb = dashboard_period_keyboard(period_prefix)
    switch_kb = dashboard_switch_keyboard()
    period_kb.inline_keyboard.extend(switch_kb.inline_keyboard)
    return period_kb


async def _send_market_dashboard(message_or_callback, period: str = "all"):
    stats = await db.get_dashboard_stats(period)
    monthly = await db.get_monthly_earnings(3)

    monthly_lines = []
    for m in monthly:
        month_str = m["month"].strftime("%b %Y") if m.get("month") else "—"
        monthly_lines.append(
            f"  {month_str}: {m['accepted_orders']} ta / {m['revenue']:,.0f} so'm"
        )
    monthly_text = "\n".join(monthly_lines) if monthly_lines else "  Ma'lumot yo'q"

    text = (
        f"📊 <b>Market</b> — {stats['period']}\n\n"
        f"🛒 Jami buyurtmalar: {stats['total_orders']}\n"
        f"✅ Qabul qilingan: {stats['accepted_orders']}\n"
        f"❌ Rad etilgan: {stats['rejected_orders']}\n"
        f"⏳ Kutilayotgan: {stats['pending_orders']}\n"
        f"💰 Daromad: {stats['total_revenue']:,.0f} so'm\n\n"
        f"📈 <b>Oxirgi oylar:</b>\n{monthly_text}"
    )

    reply_markup = await _combine_keyboards("dash_market")
    if isinstance(message_or_callback, types.CallbackQuery):
        await message_or_callback.message.edit_text(text, parse_mode="HTML", reply_markup=reply_markup)
    else:
        await message_or_callback.answer(text, parse_mode="HTML", reply_markup=reply_markup)


async def _send_warehouse_dashboard(message_or_callback, period: str = "all"):
    stats = await db.get_warehouse_stats()
    period_stats = await db.get_warehouse_dashboard_stats(period)

    items = await db.get_warehouse_items()
    low_stock_items = [i for i in items if i["quantity"] <= i["min_quantity"]]
    low_text = ""
    if low_stock_items:
        low_text = "\n⚠ <b>Kam qoldiq:</b>\n" + "\n".join(
            f"  • {i['name']} — {i['quantity']:,.0f} {i['unit']}"
            for i in low_stock_items[:5]
        )

    period_labels = {
        "today": "Bugun", "week": "Bu hafta", "month": "Bu oy",
        "year": "Bu yil", "all": "Umumiy",
    }

    text = (
        f"📦 <b>Ombor</b> — {period_labels.get(period, 'Umumiy')}\n\n"
        f"📊 Jami mahsulot: {stats['total_items']}\n"
        f"📦 Jami soni: {stats['total_stock_quantity']:,.0f}\n"
        f"⚠ Kam qoldiq: {stats['low_stock_items']} ta\n\n"
        f"📥 Kirim: {period_stats['stock_in']:,.0f} dona\n"
        f"📤 Chiqim: {period_stats['stock_out']:,.0f} dona\n"
        f"🔄 Operatsiyalar: {period_stats['transactions']} ta"
        f"{low_text}"
    )

    reply_markup = await _combine_keyboards("dash_warehouse")
    if isinstance(message_or_callback, types.CallbackQuery):
        await message_or_callback.message.edit_text(text, parse_mode="HTML", reply_markup=reply_markup)
    else:
        await message_or_callback.answer(text, parse_mode="HTML", reply_markup=reply_markup)


async def _send_dailysales_dashboard(message_or_callback, period: str = "all"):
    stats = await db.get_daily_sales_stats(period)
    monthly = await db.get_monthly_daily_sales(3)

    monthly_lines = []
    for m in monthly:
        month_str = m["month"].strftime("%b %Y") if m.get("month") else "—"
        monthly_lines.append(
            f"  {month_str}: {m['total_sales']} ta / {m['revenue']:,.0f} so'm"
        )
    monthly_text = "\n".join(monthly_lines) if monthly_lines else "  Ma'lumot yo'q"

    text = (
        f"💰 <b>Kunlik tushum</b> — {stats['period']}\n\n"
        f"📊 Jami yozuvlar: {stats['total_sales']}\n"
        f"💵 Jami summa: {stats['total_amount']:,.0f} so'm\n"
        f"📉 O'rtacha: {stats['average_sale']:,.0f} so'm\n\n"
        f"📈 <b>Oxirgi oylar:</b>\n{monthly_text}"
    )

    reply_markup = await _combine_keyboards("dash_dailysales")
    if isinstance(message_or_callback, types.CallbackQuery):
        await message_or_callback.message.edit_text(text, parse_mode="HTML", reply_markup=reply_markup)
    else:
        await message_or_callback.answer(text, parse_mode="HTML", reply_markup=reply_markup)


@router.message(F.text == "📊 Dashboard")
async def admin_dashboard_button(message: types.Message):
    if not is_admin(message.from_user.id):
        return
    await _send_market_dashboard(message)


@router.callback_query(F.data.startswith("dash_"))
async def dashboard_all_callbacks(callback: types.CallbackQuery):
    if not is_admin(callback.from_user.id):
        await callback.answer("Siz admin emassiz!", show_alert=True)
        return

    data = callback.data

    if data.startswith("dash_switch:"):
        tab = data.split(":")[1]
        if tab == "market":
            await _send_market_dashboard(callback)
        elif tab == "warehouse":
            await _send_warehouse_dashboard(callback)
        elif tab == "dailysales":
            await _send_dailysales_dashboard(callback)
        await callback.answer()
        return

    if data.startswith("dash_market:"):
        period = data.split(":", 1)[1]
        await _send_market_dashboard(callback, period)
        await callback.answer()
        return

    if data.startswith("dash_warehouse:"):
        period = data.split(":", 1)[1]
        await _send_warehouse_dashboard(callback, period)
        await callback.answer()
        return

    if data.startswith("dash_dailysales:"):
        period = data.split(":", 1)[1]
        await _send_dailysales_dashboard(callback, period)
        await callback.answer()
        return


@router.message(F.text == "📦 Mahsulotlar")
async def admin_products_button(message: types.Message):
    if not is_admin(message.from_user.id):
        return
    products = await db.get_all_products()
    if not products:
        await message.answer("Hali mahsulotlar yo'q.")
        return
    cats = {c["id"]: c["name"] for c in await db.get_categories()}
    lines = []
    for p in products:
        status = "✅"
        cat_name = cats.get(p["category_id"]) if p["category_id"] else None
        if cat_name is None:
            cat_name = "Kategoriya yo'q"
        lines.append(f"{status} #{p['id']} {p['name']} — {p['price']:,.0f} so'm ({cat_name})")
    # Send in chunks if too long
    chunk = ""
    for line in lines:
        if len(chunk) + len(line) > 3800:
            await message.answer(chunk, parse_mode="HTML")
            chunk = ""
        chunk += line + "\n"
    if chunk:
        await message.answer(chunk, parse_mode="HTML")


def _order_actions_keyboard(order_id: int) -> types.InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="✅ Qabul qilish", callback_data=f"order_accept:{order_id}")
    builder.button(text="❌ Rad etish", callback_data=f"order_reject:{order_id}")
    return builder.as_markup()


@router.message(F.text == "🛒 Buyurtmalar")
async def admin_orders_button(message: types.Message):
    if not is_admin(message.from_user.id):
        return
    from datetime import date
    orders = await db.get_orders_by_date(date.today())
    if not orders:
        await message.answer("📅 Bugun buyurtmalar yo'q.\n\nBoshqa sana uchun: <code>/orders YYYY-MM-DD</code>", parse_mode="HTML")
        return
    await message.answer(f"📅 <b>Bugun</b>: {len(orders)} ta buyurtma", parse_mode="HTML")
    for order in orders:
        emoji = {"pending": "⏳", "processing": "👨‍🍳", "delivered": "✅", "cancelled": "❌"}.get(order["status"], "📦")
        text = (
            f"{emoji} <b>Buyurtma #{order['id']}</b>\n"
            f"👤 {order['user_name'] or 'Noma\'lum'}\n"
            f"📞 {order['phone']}\n"
            f"📍 {order['address']}\n"
            f"💰 {order['total_amount']:,.0f} so'm\n"
            f"📅 {order['created_at'].strftime('%d.%m.%Y %H:%M') if order.get('created_at') else '—'}\n"
            f"Status: <b>{order['status']}</b>"
        )
        reply_markup = None
        if order["status"] in ("pending", "processing"):
            reply_markup = _order_actions_keyboard(order["id"])
        await message.answer(text, parse_mode="HTML", reply_markup=reply_markup)
