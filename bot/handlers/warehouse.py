from datetime import datetime, date

from aiogram import Router, types, F
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

from bot.config import settings
from bot.services.database import db
from bot.utils.validators import parse_price_input
from bot.utils.logger import get_logger, log_user_action

router = Router()
logger = get_logger(__name__)


class AddWarehouseItemForm(StatesGroup):
    name = State()
    unit = State()
    quantity = State()


class EditWarehouseItemForm(StatesGroup):
    item_id = State()
    field = State()
    value = State()


class AddStockForm(StatesGroup):
    item_id = State()
    quantity = State()
    notes = State()


class RemoveStockForm(StatesGroup):
    item_id = State()
    quantity = State()
    notes = State()


class DailySaleForm(StatesGroup):
    amount = State()
    notes = State()
    date = State()


def is_admin(user_id: int) -> bool:
    return user_id in settings.admin_ids


# ── Warehouse Dashboard ──

@router.message(Command("ombor"))
async def warehouse_dashboard(message: types.Message):
    if not is_admin(message.from_user.id):
        return

    try:
        items = await db.get_warehouse_items()
        stats = await db.get_warehouse_stats()

        text = (
            "📦 <b>Ombor holati</b>\n\n"
            f"📊 Jami mahsulot: {stats['total_items']}\n"
            f"📦 Jami soni: {stats['total_stock_quantity']:,.0f}\n"
            f"⚠ Kam qoldiq: {stats['low_stock_items']} ta\n\n"
        )

        if items:
            text += "<b>Mahsulotlar:</b>\n"
            for item in items:
                warning = " ⚠" if item["quantity"] <= item["min_quantity"] else ""
                text += (
                    f"  #{item['id']} {item['name']} — "
                    f"{item['quantity']:,.0f} {item['unit']}{warning}\n"
                )

        text += (
            "\nBuyruqlar:\n"
            "/ombor_add - Ombor mahsulot qo'shish\n"
            "/ombor_kirim - Mahsulotga stock qo'shish\n"
            "/ombor_chiqim - Mahsulotdan stock chiqarish\n"
            "/ombor_harakatlar - Ombor harakatlari\n"
            "/ombor_item_delete - Mahsulotni o'chirish"
        )
        await message.answer(text, parse_mode="HTML")
    except Exception as e:
        logger.error("Error in warehouse_dashboard: %s", e)
        await message.answer("❌ Xatolik yuz berdi.")


# ── Add Warehouse Item ──

@router.message(Command("ombor_add"))
async def add_item_start(message: types.Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        return
    await state.set_state(AddWarehouseItemForm.name)
    await message.answer("Mahsulot nomini kiriting:")


@router.message(AddWarehouseItemForm.name)
async def add_item_name(message: types.Message, state: FSMContext):
    name = message.text.strip()
    if not name:
        await message.answer("Nom bo'sh bo'lmasligi kerak. Qaytadan kiriting:")
        return
    await state.update_data(name=name)
    await state.set_state(AddWarehouseItemForm.unit)
    await message.answer("O'lchov birligini kiriting (masalan: dona, kg, litr):")


@router.message(AddWarehouseItemForm.unit)
async def add_item_unit(message: types.Message, state: FSMContext):
    unit = message.text.strip().lower()
    if not unit:
        unit = "dona"
    await state.update_data(unit=unit)
    await state.set_state(AddWarehouseItemForm.quantity)
    await message.answer("Boshlang'ich miqdorni kiriting (0 qoldirish mumkin):")


@router.message(AddWarehouseItemForm.quantity)
async def add_item_finish(message: types.Message, state: FSMContext):
    try:
        quantity = float(message.text.strip().replace(" ", ""))
        if quantity < 0:
            await message.answer("Miqdor 0 dan kichik bo'lmasligi kerak.")
            return
        data = await state.get_data()
        item_id = await db.create_warehouse_item(
            name=data["name"],
            unit=data["unit"],
            quantity=quantity,
        )
        if item_id:
            await message.answer(
                f"✅ <b>{data['name']}</b> omborga qo'shildi (ID: {item_id}).\n"
                f"Boshlang'ich: {quantity:,.0f} {data['unit']}.",
                parse_mode="HTML",
            )
            log_user_action(logger, message.from_user.id, "warehouse_item_added",
                          f"item_id={item_id}, name={data['name']}")
        else:
            await message.answer("❌ Xatolik yuz berdi.")
    except ValueError:
        await message.answer("Noto'g'ri miqdor. Qaytadan kiriting:")
        return
    finally:
        await state.clear()


# ── Delete Warehouse Item ──

@router.message(Command("ombor_item_delete"))
async def delete_item(message: types.Message):
    if not is_admin(message.from_user.id):
        return
    parts = message.text.strip().split()
    if len(parts) < 2:
        await message.answer("Format: <code>/ombor_item_delete ID</code>", parse_mode="HTML")
        return
    try:
        item_id = int(parts[1])
    except ValueError:
        await message.answer("Noto'g'ri ID.")
        return
    item = await db.get_warehouse_item(item_id)
    if not item:
        await message.answer("Mahsulot topilmadi.")
        return
    success = await db.delete_warehouse_item(item_id)
    if success:
        await message.answer(f"✅ <b>{item['name']}</b> ombordan o'chirildi.", parse_mode="HTML")
        log_user_action(logger, message.from_user.id, "warehouse_item_deleted",
                      f"item_id={item_id}")
    else:
        await message.answer("❌ Xatolik yuz berdi.")


# ── Add Stock (Kirim) ──

@router.message(Command("ombor_kirim"))
async def add_stock_start(message: types.Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        return
    items = await db.get_warehouse_items()
    if not items:
        await message.answer("Omborda mahsulot yo'q. Avval /ombor_add orqali mahsulot qo'shing.")
        await state.clear()
        return
    lines = "\n".join(f"#{item['id']} {item['name']} ({item['quantity']:,.0f} {item['unit']})" for item in items)
    await state.set_state(AddStockForm.item_id)
    await message.answer(f"Mahsulot ID sini kiriting:\n\n{lines}")


@router.message(AddStockForm.item_id)
async def add_stock_item(message: types.Message, state: FSMContext):
    try:
        item_id = int(message.text.strip())
        item = await db.get_warehouse_item(item_id)
        if not item:
            await message.answer("Mahsulot topilmadi. Qaytadan kiriting:")
            return
        await state.update_data(item_id=item_id)
        await state.set_state(AddStockForm.quantity)
        await message.answer(
            f"Mahsulot: <b>{item['name']}</b> (joriy: {item['quantity']:,.0f} {item['unit']})\n"
            f"Qancha qo'shiladi?",
            parse_mode="HTML",
        )
    except ValueError:
        await message.answer("Noto'g'ri ID. Qaytadan kiriting:")


@router.message(AddStockForm.quantity)
async def add_stock_quantity(message: types.Message, state: FSMContext):
    try:
        quantity = float(message.text.strip().replace(" ", ""))
        if quantity <= 0:
            await message.answer("Miqdor 0 dan katta bo'lishi kerak.")
            return
        await state.update_data(quantity=quantity)
        await state.set_state(AddStockForm.notes)
        await message.answer("Izoh (yoki «-» tashlab ketish):")
    except ValueError:
        await message.answer("Noto'g'ri miqdor. Qaytadan kiriting:")


@router.message(AddStockForm.notes)
async def add_stock_finish(message: types.Message, state: FSMContext):
    notes = None if message.text.strip() == "-" else message.text.strip()
    data = await state.get_data()
    success = await db.add_warehouse_stock(data["item_id"], data["quantity"], notes, message.from_user.id)
    if success:
        item = await db.get_warehouse_item(data["item_id"])
        await message.answer(
            f"✅ <b>{item['name']}</b> ga {data['quantity']:,.0f} {item['unit']} qo'shildi.",
            parse_mode="HTML",
        )
        log_user_action(logger, message.from_user.id, "warehouse_stock_in",
                      f"item_id={data['item_id']}, quantity={data['quantity']}")
    else:
        await message.answer("❌ Xatolik yuz berdi.")
    await state.clear()


# ── Remove Stock (Chiqim) ──

@router.message(Command("ombor_chiqim"))
async def remove_stock_start(message: types.Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        return
    items = await db.get_warehouse_items()
    if not items:
        await message.answer("Omborda mahsulot yo'q. Avval /ombor_kirim orqali stock qo'shing.")
        await state.clear()
        return
    lines = "\n".join(f"#{item['id']} {item['name']} — {item['quantity']:,.0f} {item['unit']}" for item in items)
    await state.set_state(RemoveStockForm.item_id)
    await message.answer(f"Mahsulot ID sini kiriting:\n\n{lines}")


@router.message(RemoveStockForm.item_id)
async def remove_stock_item(message: types.Message, state: FSMContext):
    try:
        item_id = int(message.text.strip())
        item = await db.get_warehouse_item(item_id)
        if not item:
            await message.answer("Mahsulot topilmadi. Qaytadan kiriting:")
            return
        if item["quantity"] <= 0:
            await message.answer("Bu mahsulot omborda mavjud emas.")
            await state.clear()
            return
        await state.update_data(item_id=item_id)
        await state.set_state(RemoveStockForm.quantity)
        await message.answer(
            f"Mahsulot: <b>{item['name']}</b> (joriy: {item['quantity']:,.0f} {item['unit']})\n"
            f"Qancha chiqariladi?",
            parse_mode="HTML",
        )
    except ValueError:
        await message.answer("Noto'g'ri ID. Qaytadan kiriting:")


@router.message(RemoveStockForm.quantity)
async def remove_stock_quantity(message: types.Message, state: FSMContext):
    try:
        quantity = float(message.text.strip().replace(" ", ""))
        if quantity <= 0:
            await message.answer("Miqdor 0 dan katta bo'lishi kerak.")
            return
        await state.update_data(quantity=quantity)
        await state.set_state(RemoveStockForm.notes)
        await message.answer("Izoh (yoki «-» tashlab ketish):")
    except ValueError:
        await message.answer("Noto'g'ri miqdor. Qaytadan kiriting:")


@router.message(RemoveStockForm.notes)
async def remove_stock_finish(message: types.Message, state: FSMContext):
    notes = None if message.text.strip() == "-" else message.text.strip()
    data = await state.get_data()
    success = await db.remove_warehouse_stock(data["item_id"], data["quantity"], notes, message.from_user.id)
    if success:
        item = await db.get_warehouse_item(data["item_id"])
        await message.answer(
            f"✅ <b>{item['name']}</b> dan {data['quantity']:,.0f} {item['unit']} chiqarildi.",
            parse_mode="HTML",
        )
        log_user_action(logger, message.from_user.id, "warehouse_stock_out",
                      f"item_id={data['item_id']}, quantity={data['quantity']}")
    else:
        await message.answer("❌ Xatolik yuz berdi yoki omborda yetarli mahsulot yo'q.")
    await state.clear()


# ── Warehouse Transactions ──

@router.message(Command("ombor_harakatlar"))
async def warehouse_transactions(message: types.Message):
    if not is_admin(message.from_user.id):
        return
    try:
        transactions = await db.get_warehouse_transactions(limit=30)
        if not transactions:
            await message.answer("Hali harakatlar yo'q.")
            return
        lines = []
        for t in transactions:
            emoji = "📥" if t["quantity_change"] > 0 else "📤"
            date_str = t["created_at"].strftime("%d.%m.%Y %H:%M") if t.get("created_at") else "—"
            lines.append(
                f"{emoji} <b>{t['product_name']}</b>\n"
                f"   {t['quantity_change']:+,.0f} dona | {date_str}\n"
                f"   Izoh: {t['notes'] or '—'}"
            )
        text = "\n\n".join(lines)
        if len(text) > 3800:
            for chunk in [text[i:i+3800] for i in range(0, len(text), 3800)]:
                await message.answer(chunk, parse_mode="HTML")
        else:
            await message.answer(text, parse_mode="HTML")
    except Exception as e:
        logger.error("Error in warehouse_transactions: %s", e)
        await message.answer("❌ Xatolik yuz berdi.")


# ── Daily Sale ──

@router.message(Command("kunlik_tushum"))
async def daily_sale_start(message: types.Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        return
    await state.set_state(DailySaleForm.amount)
    await message.answer("Kunlik tushum summasini kiriting (so'm):")


@router.message(DailySaleForm.amount)
async def daily_sale_amount(message: types.Message, state: FSMContext):
    amount = parse_price_input(message.text)
    if amount is None:
        await message.answer("Noto'g'ri summa. Qaytadan kiriting (masalan: 500000):")
        return
    await state.update_data(amount=amount)
    await state.set_state(DailySaleForm.notes)
    await message.answer("Izoh (yoki «-» tashlab ketish):")


@router.message(DailySaleForm.notes)
async def daily_sale_notes(message: types.Message, state: FSMContext):
    notes = None if message.text.strip() == "-" else message.text.strip()
    await state.update_data(notes=notes)
    await state.set_state(DailySaleForm.date)
    today = date.today().strftime("%d.%m.%Y")
    await message.answer(f"Sana (KK.OO.YYYY formatida, masalan: {today}):\n«-» yozib bugungi sanani qoldirishingiz mumkin.")


@router.message(DailySaleForm.date)
async def daily_sale_finish(message: types.Message, state: FSMContext):
    raw = message.text.strip()
    try:
        if raw == "-":
            sale_date = date.today()
        else:
            sale_date = datetime.strptime(raw, "%d.%m.%Y").date()

        data = await state.get_data()
        sale_id = await db.create_daily_sale(
            total_amount=data["amount"],
            sale_date=sale_date.isoformat(),
            notes=data["notes"],
            recorded_by=message.from_user.id,
        )
        await message.answer(
            f"✅ Kunlik tushum qo'shildi (ID: {sale_id})\n"
            f"💰 {data['amount']:,.0f} so'm\n"
            f"📅 {sale_date.strftime('%d.%m.%Y')}\n"
            f"📝 {data['notes'] or '—'}"
        )
        log_user_action(logger, message.from_user.id, "daily_sale_added", f"amount={data['amount']}, date={sale_date}")
    except ValueError:
        await message.answer("Noto'g'ri sana formati. Iltimos KK.OO.YYYY formatida kiriting (masalan: 15.03.2025):")
        return
    finally:
        await state.clear()


# ── List Daily Sales ──

@router.message(Command("kunlik_tushumlar"))
async def list_daily_sales(message: types.Message):
    if not is_admin(message.from_user.id):
        return
    try:
        sales = await db.get_daily_sales(limit=30)
        if not sales:
            await message.answer("Hali kunlik tushumlar qo'shilmagan.")
            return
        lines = []
        for s in sales:
            date_str = s["sale_date"].strftime("%d.%m.%Y") if isinstance(s["sale_date"], date) else str(s["sale_date"])
            lines.append(
                f"#{s['id']} | {date_str} | {s['total_amount']:,.0f} so'm\n"
                f"   📝 {s['notes'] or '—'}"
            )
        text = "💰 <b>Kunlik tushumlar</b>\n\n" + "\n\n".join(lines)
        if len(text) > 3800:
            for chunk in [text[i:i+3800] for i in range(0, len(text), 3800)]:
                await message.answer(chunk, parse_mode="HTML")
        else:
            await message.answer(text, parse_mode="HTML")
    except Exception as e:
        logger.error("Error in list_daily_sales: %s", e)
        await message.answer("❌ Xatolik yuz berdi.")


# ── Delete Daily Sale ──

@router.message(Command("kunlik_tushum_delete"))
async def delete_daily_sale(message: types.Message):
    if not is_admin(message.from_user.id):
        return
    parts = message.text.strip().split()
    if len(parts) < 2:
        await message.answer("Format: <code>/kunlik_tushum_delete ID</code>", parse_mode="HTML")
        return
    try:
        sale_id = int(parts[1])
    except ValueError:
        await message.answer("Noto'g'ri ID.")
        return
    success = await db.delete_daily_sale(sale_id)
    if success:
        await message.answer(f"✅ Kunlik tushum #{sale_id} o'chirildi.")
    else:
        await message.answer("Tushum topilmadi.")


# ── Button handlers for warehouse and daily sales ──

@router.message(F.text == "📦 Ombor")
async def warehouse_button(message: types.Message):
    if not is_admin(message.from_user.id):
        return
    await warehouse_dashboard(message)


@router.message(F.text == "💰 Kunlik tushum")
async def daily_sale_button(message: types.Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        return
    await daily_sale_start(message, state)
