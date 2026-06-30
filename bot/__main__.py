import asyncio
import logging

from bot.bot import bot, dp
from bot.services.database import db

logging.basicConfig(level=logging.INFO)


async def main():
    await db.connect()
    try:
        await dp.start_polling(bot)
    finally:
        await db.close()
        await bot.session.close()


if __name__ == "__main__":
    asyncio.run(main())
