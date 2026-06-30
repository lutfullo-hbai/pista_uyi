from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, WebAppInfo
from bot.config import settings


def main_keyboard() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(
                text="🛒 Magazinga kirish",
                web_app=WebAppInfo(url=settings.web_app_url),
            )],
            [KeyboardButton(text="📋 Mening buyurtmalarim")],
            [KeyboardButton(text="📞 Bog'lanish")],
        ],
        resize_keyboard=True,
    )


def admin_keyboard() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="📊 Dashboard"),
             KeyboardButton(text="📦 Mahsulotlar"),
             KeyboardButton(text="🛒 Buyurtmalar")],
            [KeyboardButton(text="📦 Ombor"),
             KeyboardButton(text="💰 Kunlik tushum")],
            [KeyboardButton(
                text="🛒 Magazinga kirish",
                web_app=WebAppInfo(url=settings.web_app_url),
            )],
        ],
        resize_keyboard=True,
    )
