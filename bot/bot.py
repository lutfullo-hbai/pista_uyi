from aiogram import Bot, Dispatcher

from bot.config import settings
from bot.handlers import start, admin, user, warehouse

bot = Bot(token=settings.bot_token)
dp = Dispatcher()

dp.include_router(start.router)
dp.include_router(admin.router)
dp.include_router(user.router)
dp.include_router(warehouse.router)
