"""
Telegram bot asosiy entry point.
"""
import logging
import signal
import sys
import asyncio

import uvicorn

from bot.bot import bot, dp
from bot.services.database import db
from bot.utils.logger import get_logger

logger = get_logger(__name__)

_shutdown_event = asyncio.Event()


def _handle_signal():
    """Signal handler for graceful shutdown."""
    logger.info("Shutdown signal received")
    _shutdown_event.set()


async def run_bot():
    """Run Telegram bot."""
    await db.connect()
    logger.info("Connected to database")
    try:
        logger.info("Starting bot polling...")
        await dp.start_polling(bot)
    finally:
        await db.close()
        await bot.session.close()
        logger.info("Bot stopped")


async def main():
    """Main entry point - start bot and/or web server."""
    # Parse command line arguments
    if "--bot-only" in sys.argv:
        await run_bot()
        return

    if "--web-only" in sys.argv:
        logger.info("Starting web server only...")
        config = uvicorn.Config(
            "web.server:app",
            host="0.0.0.0",
            port=8000,
            log_level="info"
        )
        server = uvicorn.Server(config)
        await server.serve()
        return

    # Start both bot and web server
    logger.info("Starting bot and web server...")

    bot_task = asyncio.create_task(run_bot())

    config = uvicorn.Config(
        "web.server:app",
        host="0.0.0.0",
        port=8000,
        log_level="info"
    )
    server = uvicorn.Server(config)
    web_task = asyncio.create_task(server.serve())

    # Setup signal handlers for graceful shutdown
    loop = asyncio.get_event_loop()
    for sig in (signal.SIGINT, signal.SIGTERM):
        try:
            loop.add_signal_handler(sig, _handle_signal)
        except NotImplementedError:
            pass

    # Handle Windows (no signal handlers)
    if sys.platform == "win32":
        try:
            while not _shutdown_event.is_set():
                await asyncio.sleep(1)
        except KeyboardInterrupt:
            _shutdown_event.set()
    else:
        await _shutdown_event.wait()

    logger.info("Shutting down...")
    bot_task.cancel()
    web_task.cancel()
    
    # Wait for tasks to complete
    await asyncio.gather(bot_task, web_task, return_exceptions=True)
    logger.info("Shutdown complete")


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Interrupted by user")
        sys.exit(0)

