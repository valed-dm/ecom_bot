import asyncio

from aiogram import Bot
from aiogram import Dispatcher
from aiogram.client.default import DefaultBotProperties

from ecombot.bot.handlers import admin
from ecombot.bot.handlers import admin_orders
from ecombot.bot.handlers import cart
from ecombot.bot.handlers import catalog
from ecombot.bot.handlers import checkout
from ecombot.bot.handlers import orders
from ecombot.bot.handlers import profile
from ecombot.bot.middlewares import DbSessionMiddleware
from ecombot.bot.middlewares import UserMiddleware
from ecombot.config import settings
from ecombot.db.database import AsyncSessionLocal
from ecombot.logging_setup import log


async def main() -> None:
    """
    Initializes and starts the Telegram bot.

    This function sets up the Bot and Dispatcher instances, registers
    essential middlewares for database session management and user context,
    includes all the necessary routers for handling different bot features,
    and starts the polling process.
    """
    bot = Bot(
        token=settings.BOT_TOKEN,
        default=DefaultBotProperties(parse_mode="HTML"),
    )
    dp = Dispatcher()

    dp.update.middleware(DbSessionMiddleware(session_pool=AsyncSessionLocal))
    dp.update.middleware(UserMiddleware())

    dp.include_router(admin.router)
    dp.include_router(admin_orders.router)
    dp.include_router(catalog.router)
    dp.include_router(cart.router)
    dp.include_router(checkout.router)
    dp.include_router(profile.router)
    dp.include_router(orders.router)

    log.info("Bot is starting...")
    await dp.start_polling(bot)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        log.info("Bot stopped.")
