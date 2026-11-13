import logging
from aiogram import Router, F, types, Bot
from aiogram.filters import Command
from sqlalchemy import select
from database.db import AsyncSessionLocal
from database.models import MessageLog
from services.report_service import ReportService
from config import settings

logger = logging.getLogger(__name__)
report_router = Router()


@report_router.message(Command("report", "shikoyat"))
async def handle_report_command(message: types.Message, bot: Bot):
    """
    Foydalanuvchi qoidabuzar xabarga javob (reply) qilib /report yoki /shikoyat yozganda ishlaydi
    """
    if not message.reply_to_message:
        await message.reply(
            "⚠️ Qoidalarga zid xabar ustidan shikoyat qilish uchun ushbu xabarga <b>reply (javob)</b> qilib <code>/report [sabab]</code> yozing.",
            parse_mode="HTML"
        )
        return

    target_msg = message.reply_to_message
    reporter = message.from_user
    chat_id = message.chat.id

    # Shikoyat sababini ajratib olish
    parts = message.text.split(maxsplit=1)
    reason = parts[1] if len(parts) > 1 else "Foydalanuvchi tomonidan qoidabuzarlik haqida shikoyat"

    target_text = target_msg.text or target_msg.caption or "[Media / fayl]"

    async with AsyncSessionLocal() as session:
        # Xabarni bazadan izlash
        result = await session.execute(
            select(MessageLog).where(
                MessageLog.telegram_message_id == target_msg.message_id,
                MessageLog.chat_id == chat_id
            )
        )
        db_msg = result.scalar_one_or_none()

        # Agar bazada bo'lmasa, yangi log yaratamiz
        if not db_msg:
            from moderation.pipeline import ModerationResult
            from services.message_service import MessageService
            dummy_res = ModerationResult(
                is_violation=False,
                status="REPORTED",
                detection_stage="CLEAN",
                violation_type="NONE",
                toxicity_score=50.0,
                reason="Foydalanuvchi shikoyati orqali qo'shildi",
                action_taken="NONE",
                translated_uz=target_text,
                translated_ru=target_text
            )
            sender_id = target_msg.from_user.id if target_msg.from_user else 0
            sender_name = target_msg.from_user.full_name if target_msg.from_user else "Noma'lum"
            sender_username = target_msg.from_user.username if target_msg.from_user else None

            db_msg = await MessageService.log_message(
                db=session,
                telegram_message_id=target_msg.message_id,
                chat_id=chat_id,
                chat_title=message.chat.title or "Guruh",
                user_telegram_id=sender_id,
                sender_name=sender_name,
                sender_username=sender_username,
                original_text=target_text,
                result=dummy_res
            )

        # Shikoyatni ro'yxatga olish
        report = await ReportService.create_report(
            db=session,
            message_id=db_msg.id,
            reporter_telegram_id=reporter.id,
            reporter_name=reporter.full_name,
            reason=reason
        )

    # Foydalanuvchiga tasdiq xabari
    ack_msg = await message.reply(
        "✅ <b>Shikoyatingiz qabul qilindi!</b>\nModeratorlar ko'rib chiqishadi va tegishli chora ko'riladi. Rahmat!",
        parse_mode="HTML"
    )

    # Guruhda keraksiz xabarlarni tozalash (10 soniya)
    try:
        import asyncio
        async def cleanup():
            await asyncio.sleep(10)
            try:
                await message.delete()
                await ack_msg.delete()
            except Exception:
                pass
        asyncio.create_task(cleanup())
    except Exception:
        pass

    # Admin Telegram profiliga bildirishnoma yuborish
    if settings.ADMIN_TELEGRAM_ID and settings.ADMIN_TELEGRAM_ID > 0:
        try:
            admin_alert = (
                f"🚨 <b>Yangi shikoyat kelib tushdi!</b>\n\n"
                f"📍 <b>Guruh:</b> {message.chat.title}\n"
                f"👤 <b>Shikoyatchi:</b> {reporter.full_name} (ID: {reporter.id})\n"
                f"📝 <b>Sabab:</b> {reason}\n"
                f"💬 <b>Shikoyat qilingan xabar:</b>\n<i>\"{target_text[:200]}\"</i>\n\n"
                f"Boshqaruv paneli orqali tekshirishingiz mumkin."
            )
            await bot.send_message(
                chat_id=settings.ADMIN_TELEGRAM_ID,
                text=admin_alert,
                parse_mode="HTML"
            )
        except Exception as e:
            logger.warning(f"Adminga shikoyat bildirishnomasini yuborib bo'lmadi: {e}")
