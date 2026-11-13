import asyncio
import logging
from aiogram import Bot, Dispatcher
from aiogram.types import BotCommand
from config import settings
from bot.handlers.admin import admin_router
from bot.handlers.reports import report_router
from bot.handlers.moderation import moderation_router

logger = logging.getLogger(__name__)


def create_bot_and_dispatcher():
    if not settings.BOT_TOKEN or len(settings.BOT_TOKEN) < 20:
        logger.warning("BOT_TOKEN ko'rsatilmagan yoki yaroqsiz! Telegram bot polling o'tkazib yuboriladi.")
        return None, None

    bot = Bot(token=settings.BOT_TOKEN)
    dp = Dispatcher()

    # Routerni tartib bo'yicha ulash
    dp.include_router(admin_router)
    dp.include_router(report_router)
    dp.include_router(moderation_router)

    return bot, dp


async def setup_bot_commands(bot: Bot):
    commands = [
        BotCommand(command="start", description="Bot haqida ma'lumot"),
        BotCommand(command="check", description="Matnni AI orqali tekshirish"),
        BotCommand(command="stats", description="Moderatsiya statistikasi"),
        BotCommand(command="report", description="Xabar ustidan shikoyat qilish"),
    ]
    try:
        await bot.set_my_commands(commands)
    except Exception as e:
        logger.warning(f"Bot buyruqlarini sozlab bo'lmadi: {e}")


async def run_bot():
    bot, dp = create_bot_and_dispatcher()
    if not bot or not dp:
        logger.info("Bot ishga tushirilmadi (BOT_TOKEN .env faylida ko'rsatilmagan).")
        # Do not block, just wait indefinitely or return
        while True:
            await asyncio.sleep(3600)

    logger.info("Telegram Bot ishga tushmoqda...")
    await setup_bot_commands(bot)
    try:
        await dp.start_polling(bot)
    finally:
        await bot.session.close()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(run_bot())
