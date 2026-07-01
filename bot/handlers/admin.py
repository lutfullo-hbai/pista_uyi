import io
import json
import os
import uuid
import zipfile
from datetime import date
from pathlib import Path

from aiogram import Router, types, F
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.utils.keyboard import InlineKeyboardBuilder

from bot.config import settings
from bot.services.database import db
from bot.utils.validators import parse_price_input
from bot.utils.logger import get_logger, log_user_action

router = Router()
logger = get_logger(__name__)

UPLOAD_DIR = "web/static/uploads"


class ProductForm(StatesGroup):
    name = State()
    description = State()
    price = State()
    image = State()
    category_id = State()


class CategoryForm(StatesGroup):
    name = State()


class EditProductForm(StatesGroup):
    field = State()
    value = State()


class OrderStatusForm(StatesGroup):
    new_status = State()


class BroadcastForm(StatesGroup):
    message = State()


class ClearDataForm(StatesGroup):
    confirm = State()


VALID_STATUSES = ["pending", "processing", "delivered", "cancelled"]


def is_admin(user_id: int) -> bool:
    return user_id in settings.admin_ids


STATUS_EMOJI = {
    "pending": "⏳",
    "processing": "👨‍🍳",
    "delivered": "✅",
    "cancelled": "❌",
}


def order_actions_keyboard(order_id: int) -> types.InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="✅ Qabul qilish", callback_data=f"order_accept:{order_id}")
    builder.button(text="❌ Rad etish", callback_data=f"order_reject:{order_id}")
    return builder.as_markup()


async def _ask_category(message: types.Message, state: FSMContext):
    categories = await db.get_categories()
    if not categories:
        await message.answer("Avval kategoriya qo'shing: /add_category")
        await state.clear()
        return
    lines = "\n".join(f"{c['id']}. {c['name']}" for c in categories)
    await state.set_state(ProductForm.category_id)
    await message.answer(f"Kategoriya ID sini kiriting:\n\n{lines}")


# ── Dashboard ──

@router.message(Command("admin"))
async def admin_panel(message: types.Message):
    if not is_admin(message.from_user.id):
        return
    
    try:
        stats = await db.get_stats()
        text = (
            "📊 <b>Admin panel</b>\n\n"
            f"📦 Mahsulotlar: {stats['total_products']}\n"
            f"📁 Kategoriyalar: {stats['total_categories']}\n"
            f"🛒 Buyurtmalar: {stats['total_orders']} ({stats['pending_orders']} kutilmoqda)\n"
            f"💰 Jami daromad: {stats['total_revenue']:,.0f} so'm\n\n"
            "Buyruqlar:\n"
            "/add_category - Yangi kategoriya\n"
            "/add_product - Yangi mahsulot\n"
            "/products - Mahsulotlar ro'yxati\n"
            "/edit_product - Mahsulotni tahrirlash\n"
            "/delete_product - Mahsulotni o'chirish\n"
            "/toggle_product - Mahsulotni aktiv/passiv qilish\n"
            "/orders - Buyurtmalar\n"
            "/order - Buyurtma tafsilotlari\n"
            "/status - Buyurtma statusini o'zgartirish\n"
            "/broadcast - Xabar yuborish\n\n"
            "📦 <b>Ombor:</b>\n"
            "/ombor - Ombor holati\n"
            "/ombor_kirim - Stock qo'shish\n"
            "/ombor_chiqim - Stock chiqarish\n"
            "/ombor_harakatlar - Harakatlar tarixi\n\n"
            "💰 <b>Kunlik tushum:</b>\n"
            "/kunlik_tushum - Tushum qo'shish\n"
            "/kunlik_tushumlar - Tushumlar ro'yxati\n"
            "/kunlik_tushum_delete - Tushumni o'chirish"
        )
        await message.answer(text, parse_mode="HTML")
        log_user_action(logger, message.from_user.id, "admin_panel_accessed")
    except Exception as e:
        logger.error("Error in admin_panel: %s", e)
        await message.answer("❌ Xatolik yuz berdi. Qaytadan urinib ko'ring.")


# ── Add Category ──

@router.message(Command("add_category"))
async def add_category_start(message: types.Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        return
    await state.set_state(CategoryForm.name)
    await message.answer("Kategoriya nomini kiriting:")


@router.message(CategoryForm.name)
async def add_category_finish(message: types.Message, state: FSMContext):
    name = message.text.strip()
    if not name or len(name) < 2:
        await message.answer("Nom 2 ta belgidan kam bo'lmasligi kerak.")
        return
    
    try:
        cat_id = await db.create_category(name)
        await message.answer(f"✅ «{name}» kategoriyasi qo'shildi (ID: {cat_id}).")
        log_user_action(logger, message.from_user.id, "category_added", f"name={name}")
    except Exception as e:
        logger.error("Error adding category: %s", e)
        await message.answer("❌ Kategoriya qo'shishda xatolik yuz berdi.")
    finally:
        await state.clear()


# ── Add Product ──

@router.message(Command("add_product"))
async def add_product_start(message: types.Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        return
    await state.set_state(ProductForm.name)
    await message.answer("Mahsulot nomini kiriting:")


@router.message(ProductForm.name)
async def add_product_name(message: types.Message, state: FSMContext):
    name = message.text.strip()
    if not name or len(name) < 2:
        await message.answer("Nom 2 ta belgidan kam bo'lmasligi kerak.")
        return
    await state.update_data(name=name)
    await state.set_state(ProductForm.description)
    await message.answer("Mahsulot tavsifini kiriting (yoki «-» tashlab ketish):")


@router.message(ProductForm.description)
async def add_product_description(message: types.Message, state: FSMContext):
    desc = message.text.strip()
    await state.update_data(description=None if desc == "-" else desc)
    await state.set_state(ProductForm.price)
    await message.answer("Mahsulot narxini kiriting (so'm):")


@router.message(ProductForm.price)
async def add_product_price(message: types.Message, state: FSMContext):
    price = parse_price_input(message.text)
    if price is None:
        await message.answer("Noto'g'ri narx. Qaytadan kiriting (masalan: 30000):")
        return
    
    await state.update_data(price=price)
    await state.set_state(ProductForm.image)
    await message.answer("Mahsulot rasmini yuboring (yoki «-» yozib tashlab ketish):")


@router.message(ProductForm.image, F.photo)
async def add_product_image_photo(message: types.Message, state: FSMContext):
    try:
        os.makedirs(UPLOAD_DIR, exist_ok=True)
        photo = message.photo[-1]
        tg_file = await message.bot.get_file(photo.file_id)
        ext = os.path.splitext(tg_file.file_path or ".jpg")[1] or ".jpg"
        filename = f"{uuid.uuid4().hex}{ext}"
        filepath = os.path.join(UPLOAD_DIR, filename)
        await message.bot.download_file(tg_file.file_path, destination=filepath)
        await state.update_data(image_url=f"/static/uploads/{filename}")
        await message.answer("✅ Rasm qabul qilindi.")
        await _ask_category(message, state)
    except Exception as e:
        logger.error("Error uploading photo: %s", e)
        await message.answer("❌ Rasm yuklashda xatolik. Qaytadan urinib ko'ring.")


@router.message(ProductForm.image, F.text)
async def add_product_image_text(message: types.Message, state: FSMContext):
    url = message.text.strip()
    await state.update_data(image_url=None if url == "-" else url)
    await _ask_category(message, state)


@router.message(ProductForm.category_id)
async def add_product_finish(message: types.Message, state: FSMContext):
    try:
        cat_id = int(message.text.strip())
        category = await db.get_category(cat_id)
        if not category:
            await message.answer("Noto'g'ri kategoriya ID. Qaytadan kiriting:")
            return
        
        data = await state.get_data()
        product_id = await db.create_product(
            category_id=cat_id,
            name=data["name"],
            description=data["description"],
            price=data["price"],
            image_url=data.get("image_url"),
        )
        await message.answer(f"✅ «{data['name']}» mahsuloti qo'shildi (ID: {product_id}).")
        log_user_action(logger, message.from_user.id, "product_added", 
                       f"product_id={product_id}, name={data['name']}")
    except ValueError:
        await message.answer("Noto'g'ri ID. Qaytadan kiriting:")
        return
    except Exception as e:
        logger.error("Error adding product: %s", e)
        await message.answer("❌ Mahsulot qo'shishda xatolik yuz berdi.")
    finally:
        await state.clear()


# ── List Products ──

@router.message(Command("products"))
async def list_products(message: types.Message):
    if not is_admin(message.from_user.id):
        return
    
    try:
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
            lines.append(
                f"{status} #{p['id']} <b>{p['name']}</b> — {p['price']:,.0f} so'm\n"
                f"   Kategoriya: {cat_name}"
            )
        
        # Send in chunks if too long
        text = "\n\n".join(lines)
        if len(text) > 3800:
            for chunk in [text[i:i+3800] for i in range(0, len(text), 3800)]:
                await message.answer(chunk, parse_mode="HTML")
        else:
            await message.answer(text, parse_mode="HTML")
    except Exception as e:
        logger.error("Error listing products: %s", e)
        await message.answer("❌ Xatolik yuz berdi.")


# ── Edit Product ──

@router.message(Command("edit_product"))
async def edit_product_start(message: types.Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        return
    await state.set_state(EditProductForm.field)
    await message.answer(
        "Mahsulot ID sini va o'zgartirmoqchi bo'lgan maydonni kiriting:\n"
        "Format: <code>ID maydon</code>\n\n"
        "Maydonlar: name, description, price, image_url\n"
        "Misol: <code>5 name</code>",
        parse_mode="HTML",
    )


@router.message(EditProductForm.field)
async def edit_product_field(message: types.Message, state: FSMContext):
    parts = message.text.strip().split(maxsplit=1)
    if len(parts) != 2:
        await message.answer("Format: <code>ID maydon</code> (masalan: <code>5 name</code>)", parse_mode="HTML")
        return
    try:
        product_id = int(parts[0])
    except ValueError:
        await message.answer("Noto'g'ri ID.")
        return
    field = parts[1].strip()
    if field not in ("name", "description", "price", "image_url"):
        await message.answer("Noto'g'ri maydon. Tanlang: name, description, price, image_url")
        return
    product = await db.get_product(product_id)
    if not product:
        await message.answer("Mahsulot topilmadi.")
        await state.clear()
        return
    await state.update_data(product_id=product_id, field=field)
    await state.set_state(EditProductForm.value)
    current = product.get(field, "—")
    await message.answer(f"Joriy qiymat: <code>{current}</code>\nYangi qiymatni kiriting:", parse_mode="HTML")


@router.message(EditProductForm.value)
async def edit_product_value(message: types.Message, state: FSMContext):
    data = await state.get_data()
    product_id = data["product_id"]
    field = data["field"]
    value = message.text.strip()
    kwargs = {}
    if field == "price":
        try:
            text = value.lower()
            for word in ["sum", "so'm", "soʻm", "som", "sóm", "сум"]:
                text = text.replace(word, "")
            text = text.strip().replace(" ", "")
            kwargs["price"] = float(text)
        except ValueError:
            await message.answer("Noto'g'ri narx. Qaytadan kiriting:")
            return
    elif field == "description":
        kwargs["description"] = None if value == "-" else value
    else:
        kwargs[field] = value
    success = await db.update_product(product_id, **kwargs)
    if success:
        await message.answer(f"✅ Mahsulot #{product_id} yangilandi.")
    else:
        await message.answer("Xatolik yuz berdi.")
    await state.clear()


# ── Delete Product ──

@router.message(Command("delete_product"))
async def delete_product(message: types.Message):
    if not is_admin(message.from_user.id):
        return
    parts = message.text.strip().split()
    if len(parts) < 2:
        await message.answer("Format: <code>/delete_product ID</code>", parse_mode="HTML")
        return
    try:
        product_id = int(parts[1])
    except ValueError:
        await message.answer("Noto'g'ri ID.")
        return
    product = await db.get_product(product_id)
    if not product:
        await message.answer("Mahsulot topilmadi.")
        return
    success = await db.delete_product(product_id)
    if success:
        await message.answer(f"✅ Mahsulot #{product_id} o'chirildi.")
    else:
        await message.answer("❌ Mahsulotni o'chirib bo'lmadi, chunki buyurtmalarda mavjud.")


# ── Toggle Product Availability ──

@router.message(Command("toggle_product"))
async def toggle_product(message: types.Message):
    if not is_admin(message.from_user.id):
        return
    parts = message.text.strip().split()
    if len(parts) < 2:
        await message.answer("Format: <code>/toggle_product ID</code>", parse_mode="HTML")
        return
    try:
        product_id = int(parts[1])
    except ValueError:
        await message.answer("Noto'g'ri ID.")
        return
    result = await db.toggle_product_availability(product_id)
    if result is None:
        await message.answer("Mahsulot topilmadi.")
    else:
        status = "aktiv" if result else "passiv"
        await message.answer(f"✅ Mahsulot #{product_id} {status} holatiga o'tkazildi.")


# ── List Orders ──

@router.message(Command("orders"))
async def list_orders(message: types.Message):
    if not is_admin(message.from_user.id):
        return
    parts = message.text.strip().split()
    status_filter = parts[1].lower() if len(parts) > 1 and parts[1].lower() in VALID_STATUSES else None
    orders = await db.get_orders(limit=20, status=status_filter)
    if not orders:
        await message.answer("Buyurtmalar topilmadi.")
        return
    for order in orders:
        emoji = STATUS_EMOJI.get(order["status"], "📦")
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
            reply_markup = order_actions_keyboard(order["id"])
        await message.answer(text, parse_mode="HTML", reply_markup=reply_markup)


# ── Single Order Details ──

@router.message(Command("order"))
async def order_detail(message: types.Message):
    if not is_admin(message.from_user.id):
        return
    parts = message.text.strip().split()
    if len(parts) < 2:
        await message.answer("Format: <code>/order ID</code>", parse_mode="HTML")
        return
    try:
        order_id = int(parts[1])
    except ValueError:
        await message.answer("Noto'g'ri ID.")
        return
    order = await db.get_order(order_id)
    if not order:
        await message.answer("Buyurtma topilmadi.")
        return
    emoji = STATUS_EMOJI.get(order["status"], "📦")
    items_text = "\n".join(
        f"  • {i['product_name']} × {i['quantity']} = {i['price'] * i['quantity']:,.0f} so'm"
        for i in order["items"]
    )
    text = (
        f"{emoji} <b>Buyurtma #{order['id']}</b>\n"
        f"👤 {order['user_name'] or 'Noma\'lum'}\n"
        f"📞 {order['phone']}\n"
        f"📍 {order['address']}\n"
        f"📦 Mahsulotlar:\n{items_text}\n"
        f"💰 Jami: {order['total_amount']:,.0f} so'm\n"
        f"📅 {order['created_at'].strftime('%d.%m.%Y %H:%M') if order.get('created_at') else '—'}\n"
        f"Status: <b>{order['status']}</b>"
    )
    reply_markup = None
    if order["status"] in ("pending", "processing"):
        reply_markup = order_actions_keyboard(order["id"])
    await message.answer(text, parse_mode="HTML", reply_markup=reply_markup)


# ── Accept / Reject Order (Inline Callbacks) ──

@router.callback_query(F.data.startswith("order_accept:"))
async def accept_order_callback(callback: types.CallbackQuery):
    if not is_admin(callback.from_user.id):
        await callback.answer("Siz admin emassiz!", show_alert=True)
        return
    order_id = int(callback.data.split(":")[1])
    success = await db.update_order_status(order_id, "delivered", callback.from_user.id)
    if success:
        await callback.message.edit_reply_markup(reply_markup=None)
        await callback.message.answer(
            f"✅ <b>Buyurtma #{order_id}</b> qabul qilindi — yetkazib berilgan.",
            parse_mode="HTML",
        )
        await callback.answer("✅ Qabul qilindi!", show_alert=False)
        log_user_action(logger, callback.from_user.id, "order_accepted", f"order_id={order_id}")
    else:
        await callback.answer("❌ Xatolik yuz berdi.", show_alert=True)


@router.callback_query(F.data.startswith("order_reject:"))
async def reject_order_callback(callback: types.CallbackQuery):
    if not is_admin(callback.from_user.id):
        await callback.answer("Siz admin emassiz!", show_alert=True)
        return
    order_id = int(callback.data.split(":")[1])
    success = await db.update_order_status(order_id, "cancelled", callback.from_user.id)
    if success:
        await callback.message.edit_reply_markup(reply_markup=None)
        await callback.message.answer(
            f"❌ <b>Buyurtma #{order_id}</b> rad etildi — bekor qilingan.",
            parse_mode="HTML",
        )
        await callback.answer("❌ Rad etildi!", show_alert=False)
        log_user_action(logger, callback.from_user.id, "order_rejected", f"order_id={order_id}")
    else:
        await callback.answer("❌ Xatolik yuz berdi.", show_alert=True)


# ── Change Order Status ──

@router.message(Command("status"))
async def status_change_start(message: types.Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        return
    parts = message.text.strip().split()
    if len(parts) < 2:
        await message.answer("Format: <code>/status ID</code>", parse_mode="HTML")
        return
    try:
        order_id = int(parts[1])
    except ValueError:
        await message.answer("Noto'g'ri ID.")
        return
    order = await db.get_order(order_id)
    if not order:
        await message.answer("Buyurtma topilmadi.")
        return
    await state.update_data(order_id=order_id)
    await state.set_state(OrderStatusForm.new_status)
    buttons = "\n".join(f"• {s}" for s in VALID_STATUSES)
    await message.answer(
        f"Buyurtma #{order_id} uchun yangi statusni kiriting:\n\n{buttons}\n\n"
        f"Joriy status: <b>{order['status']}</b>",
        parse_mode="HTML",
    )


@router.message(OrderStatusForm.new_status)
async def status_change_finish(message: types.Message, state: FSMContext):
    new_status = message.text.strip().lower()
    if new_status not in VALID_STATUSES:
        await message.answer(f"Noto'g'ri status. Tanlang: {', '.join(VALID_STATUSES)}")
        return
    data = await state.get_data()
    success = await db.update_order_status(data["order_id"], new_status, message.from_user.id)
    if success:
        emoji = STATUS_EMOJI.get(new_status, "📦")
        await message.answer(f"{emoji} Buyurtma #{data['order_id']} statusi <b>{new_status}</b> ga o'zgartirildi.", parse_mode="HTML")
    else:
        await message.answer("Xatolik yuz berdi.")
    await state.clear()


# ── Broadcast ──

@router.message(Command("broadcast"))
async def broadcast_start(message: types.Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        return
    await state.set_state(BroadcastForm.message)
    await message.answer("Yubormoqchi bo'lgan xabaringizni kiriting:")


@router.message(BroadcastForm.message)
async def broadcast_send(message: types.Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        return
    text = message.text
    if message.photo:
        text = message.caption or ""
    user_ids = await db.get_unique_user_ids()
    sent = 0
    failed = 0
    for uid in user_ids:
        try:
            if message.photo:
                await message.bot.send_photo(uid, message.photo[-1].file_id, caption=text)
            else:
                await message.bot.send_message(uid, text)
            sent += 1
        except Exception:
            failed += 1
    await message.answer(f"✅ Xabar yuborildi: {sent} ta foydalanuvchiga.\n"
                         f"❌ Yuborilmadi: {failed} ta.")
    await state.clear()


# ── Clear All Data ──

@router.message(Command("clear_data"))
async def clear_data_start(message: types.Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        return
    await state.set_state(ClearDataForm.confirm)
    await message.answer(
        "⚠️ <b>DIQQAT! Mahsulot katalogi tozalanadi:</b>\n\n"
        "❌ Kategoriyalar o'chadi\n"
        "❌ Mahsulotlar yashirinadi (is_available = False)\n"
        "❌ Foydalanuvchi savatlari tozalanadi\n\n"
        "✅ <b>Saqlanadi:</b> Buyurtmalar, Ombor, Kunlik tushumlar, Foydalanuvchilar\n\n"
        "Tasdiqlash uchun <code>ha</code> deb yozing:",
        parse_mode="HTML",
    )


@router.message(ClearDataForm.confirm)
async def clear_data_confirm(message: types.Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        return
    if message.text.strip().lower() not in ("ha", "yes", "да"):
        await message.answer("Bekor qilindi.")
        await state.clear()
        return
    try:
        await db.clear_all_tables()
        await message.answer("✅ Barcha ma'lumotlar o'chirildi.")
        log_user_action(logger, message.from_user.id, "data_cleared")
    except Exception as e:
        logger.error("Error clearing data: %s", e)
        await message.answer("❌ Xatolik yuz berdi.")
    finally:
        await state.clear()


# ── Data Export ──

@router.message(Command("data_export"))
async def data_export(message: types.Message):
    if not is_admin(message.from_user.id):
        return
    try:
        await message.answer("⏳ Ma'lumotlar tayyorlanmoqda...")
        data = await db.export_all_data()
        buf = io.BytesIO()
        with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
            zf.writestr("data.json", json.dumps(data, ensure_ascii=False, indent=2, default=str))
            uploads_dir = Path("web/static/uploads")
            if uploads_dir.is_dir():
                for fpath in uploads_dir.iterdir():
                    if fpath.is_file():
                        zf.write(fpath, f"images/{fpath.name}")
        buf.seek(0)
        today = date.today().isoformat()
        doc = types.BufferedInputFile(buf.read(), filename=f"backup_{today}.zip")
        await message.answer_document(doc, caption="✅ Ma'lumotlar export qilindi.")
        log_user_action(logger, message.from_user.id, "data_exported")
    except Exception as e:
        logger.error("Error exporting data: %s", e)
        await message.answer("❌ Xatolik yuz berdi.")
