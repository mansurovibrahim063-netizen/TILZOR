import asyncio
import logging
from aiogram import Router, F, types, Bot
from aiogram.filters import Command
from aiogram.enums import ChatType
from database.db import AsyncSessionLocal
from database.models import MessageLog
from moderation.pipeline import pipeline
from services.message_service import MessageService
from config import settings

logger = logging.getLogger(__name__)
moderation_router = Router()


@moderation_router.message(
    F.chat.type.in_({ChatType.GROUP, ChatType.SUPERGROUP}),
    F.text | F.caption
)
async def handle_group_message(message: types.Message, bot: Bot):
    # Botning o'z xabarlarini e'tiborsiz qoldirish
    if message.from_user and message.from_user.is_bot:
        return

    text = message.text or message.caption or ""
    if not text.strip():
        return

    user_id = message.from_user.id
    user_name = message.from_user.full_name
    username = message.from_user.username
    chat_id = message.chat.id
    chat_title = message.chat.title or "Guruh"

    # Guruh administratorlarini tekshirishdan ozod qilish (agar kerak bo'lsa)
    # Admin tekshiruvi:
    try:
        member = await bot.get_chat_member(chat_id, user_id)
        if member.status in ["administrator", "creator"]:
            # Adminlar uchun faqat log yozish, lekin o'chirmaslik
            is_admin = True
        else:
            is_admin = False
    except Exception:
        is_admin = False

    # 2 bosqichli tekshiruv (Regex + Gemini AI)
    mod_result = await pipeline.evaluate_message(user_id=user_id, text=text)

    # Natijani bazaga saqlash
    async with AsyncSessionLocal() as session:
        log_entry = await MessageService.log_message(
            db=session,
            telegram_message_id=message.message_id,
            chat_id=chat_id,
            chat_title=chat_title,
            user_telegram_id=user_id,
            sender_name=user_name,
            sender_username=username,
            original_text=text,
            result=mod_result
        )

    # Agar qoidabuzarlik aniqlansa va foydalanuvchi oddiy a'zo bo'lsa
    if mod_result.is_violation and not is_admin:
        try:
            # 1. Xabarni o'chirish
            await message.delete()

            # 2. Foydalanuvchiga ogohlantirish yuborish
            warning_text = (
                f"🛡 <b>AI-Moderator ogohlantirishi</b>\n"
                f"👤 Foydalanuvchi: <a href=\"tg://user?id={user_id}\">{user_name}</a>\n"
                f"🚫 <b>Qoidabuzarlik turi:</b> {mod_result.violation_type}\n"
                f"⚠️ <b>Sabab:</b> {mod_result.reason}\n"
                f"🔍 <b>Aniqlash bosqichi:</b> {mod_result.detection_stage}\n"
                f"📊 <b>Toksiklik:</b> {mod_result.toxicity_score:.0f}%\n"
                f"\n<i>Iltimos, guruh qoidalariga rioya qiling!</i>"
            )

            warn_msg = await bot.send_message(
                chat_id=chat_id,
                text=warning_text,
                parse_mode="HTML"
            )

            # Guruhni toza saqlash uchun ogohlantirish xabarini 15 soniyadan keyin avtomatik o'chirish
            async def delete_warning_later(msg_id: int):
                await asyncio.sleep(15)
                try:
                    await bot.delete_message(chat_id=chat_id, message_id=msg_id)
                except Exception:
                    pass

            asyncio.create_task(delete_warning_later(warn_msg.message_id))

            # 3. Agar 3 ta ogohlantirish to'plangan bo'lsa, guruhda yozishni cheklash (mute)
            if log_entry.action_taken == "BANNED":
                try:
                    await bot.restrict_chat_member(
                        chat_id=chat_id,
                        user_id=user_id,
                        permissions=types.ChatPermissions(
                            can_send_messages=False,
                            can_send_media_messages=False,
                            can_send_other_messages=False
                        )
                    )
                    ban_notice = await bot.send_message(
                        chat_id=chat_id,
                        text=f"⛔ Foydalanuvchi <a href=\"tg://user?id={user_id}\">{user_name}</a> 3 marta qoida buzganligi sababli yozish huquqidan mahrum qilindi.",
                        parse_mode="HTML"
                    )
                    asyncio.create_task(delete_warning_later(ban_notice.message_id))
                except Exception as ex:
                    logger.warning(f"Foydalanuvchini cheklab bo'lmadi: {ex}")

        except Exception as e:
            logger.error(f"Xabarni o'chirish yoki ogohlantirishda xatolik: {e}")
