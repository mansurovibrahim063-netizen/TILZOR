import asyncio
import argparse
import logging
import sys
import uvicorn
from config import settings
from database.db import init_db
from database.seed import seed_demo_data

# Logging sozlash
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger("AI-Moderator")


async def run_web_server():
    """FastAPI Web Boshqaruv Panelini ishga tushirish"""
    from web.app import app
    config = uvicorn.Config(
        app=app,
        host=settings.WEB_HOST,
        port=settings.WEB_PORT,
        log_level="info",
        access_log=False
    )
    server = uvicorn.Server(config)
    logger.info(f"🌐 Web Admin Panel ishga tushdi: http://{settings.WEB_HOST}:{settings.WEB_PORT}")
    await server.serve()


async def run_telegram_bot():
    """Telegram Botni ishga tushirish"""
    from bot.main import run_bot
    await run_bot()


async def main():
    parser = argparse.ArgumentParser(description="AI-Moderator Tizimi")
    parser.add_argument("--web-only", action="store_true", help="Faqat Web Admin panelni ishga tushirish")
    parser.add_argument("--bot-only", action="store_true", help="Faqat Telegram botni ishga tushirish")
    parser.add_argument("--seed", action="store_true", help="Baza uchun sinov demo ma'lumotlarini yuklash")
    args = parser.parse_args()

    logger.info("==================================================")
    logger.info("🛡️  AI-MODERATOR TIZIMI ISHGA TUSHMOQDA...")
    logger.info("==================================================")

    # 1. Ma'lumotlar bazasini initsializatsiya qilish
    await init_db()
    logger.info("✅ SQLite ma'lumotlar bazasi tayyor.")

    # 2. Demo ma'lumotlarni yuklash (agar baza bo'sh bo'lsa yoki --seed berilsa)
    await seed_demo_data()

    tasks = []

    if args.web_only:
        logger.info("Rejim: Faqat Web Admin Panel")
        tasks.append(run_web_server())
    elif args.bot_only:
        logger.info("Rejim: Faqat Telegram Bot")
        tasks.append(run_telegram_bot())
    else:
        logger.info("Rejim: Web Admin Panel + Telegram Bot (Parallel)")
        tasks.append(run_web_server())
        tasks.append(run_telegram_bot())

    await asyncio.gather(*tasks)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logger.info("AI-Moderator to'xtatildi.")
