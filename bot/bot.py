from aiogram import Bot, Dispatcher
from aiogram.types import TelegramObject

from bot.config import settings
from bot.handlers import start, admin, user, warehouse
from bot.services.database import db
from bot.utils.logger import get_logger

bot = Bot(token=settings.bot_token)
dp = Dispatcher()
logger = get_logger(__name__)


@dp.update.outer_middleware
async def user_tracking_middleware(handler, event: TelegramObject, data: dict):
    user = None
    if hasattr(event, "from_user") and event.from_user:
        user = event.from_user
    elif hasattr(event, "message") and event.message and event.message.from_user:
        user = event.message.from_user
    elif hasattr(event, "callback_query") and event.callback_query and event.callback_query.from_user:
        user = event.callback_query.from_user
    if user and not user.is_bot:
        try:
            await db.save_user(
                user_id=user.id,
                username=user.username,
                first_name=user.first_name,
                last_name=user.last_name,
                language_code=user.language_code,
                is_premium=getattr(user, "is_premium", False),
            )
        except Exception:
            pass
    return await handler(event, data)


dp.include_router(start.router)
dp.include_router(admin.router)
dp.include_router(user.router)
dp.include_router(warehouse.router)
