"""Entry point — ربات VPN Telegram."""

from __future__ import annotations

import asyncio
import logging

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage

from bot.config import settings
from bot.database.repository import ensure_default_settings
from bot.database.session import async_session, init_db
from bot.handlers import setup_routers
from bot.middlewares.db_session import DbSessionMiddleware
from bot.middlewares.throttling import ThrottlingMiddleware
from bot.utils.logging_setup import setup_logging

logger = logging.getLogger(__name__)


async def on_startup(bot: Bot) -> None:
    """راه‌اندازی اولیه."""
    await init_db()
    async with async_session() as session:
        await ensure_default_settings(session)

    me = await bot.get_me()
    logger.info("ربات @%s آماده است.", me.username)


async def main() -> None:
    """اجرای ربات."""
    setup_logging()
    settings.validate()

    bot = Bot(
        token=settings.bot_token,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )
    dp = Dispatcher(storage=MemoryStorage())

    # Middlewares
    dp.update.middleware(DbSessionMiddleware())
    dp.message.middleware(ThrottlingMiddleware(settings.throttle_rate))
    dp.callback_query.middleware(ThrottlingMiddleware(settings.throttle_rate))

    dp.include_router(setup_routers())
    dp.startup.register(on_startup)

    logger.info("در حال شروع polling...")
    await dp.start_polling(bot)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logger.info("ربات متوقف شد.")
