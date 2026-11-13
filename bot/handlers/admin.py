import logging
from aiogram import Router, types, Bot
from aiogram.filters import Command, CommandObject
from aiogram.enums import ChatType
from database.db import AsyncSessionLocal
from database.models import User
from services.message_service import MessageService
from moderation.pipeline import pipeline
from config import settings
from sqlalchemy import select

logger = logging.getLogger(__name__)
admin_router = Router()


@admin_router.message(Command("start"))
async def cmd_start(message: types.Message):
    await message.reply(
        "👋 <b>Assalomu alaykum! Men AI-Moderator botman.</b>\n\n"
        "Men guruhlarda quyidagi vazifalarni avtomatik bajara olaman:\n"
        "• 🚫 <b>Spam va reklamalarni tozalash</b>\n"
        "• 🔗 <b>Havolalarni bloklash (saytlar va Telegram kanallari)</b>\n"
        "• 🤬 <b>Ochiq va yashirin haqoratlarni aniqlash</b>\n"
        "• 📢 <b>Taqiqlangan chaqiriqlarni (CTA) aniqlash</b>\n"
        "• 🧠 <b>Gemini AI yordamida chuqur kontekstual tahlil</b>\n"
        "• 🌐 <b>Har bir xabarni avtomatik o'zbek va rus tillariga tarjima qilish</b>\n"
        "• 🚨 <b>Foydalanuvchilar shikoyatlarini qabul qilish</b>\n\n"
        "Meni guruhga qo'shib, <b>Administrator</b> huquqlarini bering.\n\n"
        "Buyruqlar:\n"
        "• <code>/check [matn]</code> — matnni 2 bosqichli tekshirish\n"
        "• <code>/stats</code> — moderatsiya statistikasi\n"
        "• <code>/report</code> — (xabarga reply qilib) shikoyat yuborish",
        parse_mode="HTML"
    )


@admin_router.message(Command("check"))
async def cmd_check(message: types.Message, command: CommandObject):
    """Matnni bot chatida tezkor tekshirish"""
    if not command.args:
        await message.reply("Tekshirish uchun matn kiriting:\nMasalan: <code>/check Salom do'stlar</code>", parse_mode="HTML")
        return

    test_text = command.args
    status_msg = await message.reply("⏳ <i>Matn 2 bosqichli tekshiruvdan o'tkazilmoqda...</i>", parse_mode="HTML")

    res = await pipeline.evaluate_message(user_id=message.from_user.id, text=test_text)

    status_icon = "🔴 BLOKLANDI" if res.is_violation else "🟢 RUXSAT BERILDI"
    
    reply_text = (
        f"<b>{status_icon}</b>\n\n"
        f"📋 <b>Asl matn:</b> {test_text}\n"
        f"⚙️ <b>Bosqich:</b> {res.detection_stage}\n"
        f"🏷 <b>Qoidabuzarlik turi:</b> {res.violation_type}\n"
        f"📊 <b>Toksiklik darajasi:</b> {res.toxicity_score:.0f}%\n"
        f"📝 <b>Sabab:</b> {res.reason}\n\n"
        f"🇺🇿 <b>O'zbekcha tarjima:</b>\n{res.translated_uz}\n\n"
        f"🇷🇺 <b>Ruscha tarjima:</b>\n{res.translated_ru}"
    )

    await status_msg.edit_text(reply_text, parse_mode="HTML")


@admin_router.message(Command("stats"))
async def cmd_stats(message: types.Message):
    """Bugungi va umumiy statistika"""
    async with AsyncSessionLocal() as session:
        stats = await MessageService.get_statistics(session)

    stats_text = (
        f"📊 <b>AI-Moderator Statistikasi</b>\n\n"
        f"📅 <b>Bugun:</b>\n"
        f"• Tekshirilgan: <b>{stats['today_messages']}</b> ta\n"
        f"• Bloklangan: <b>{stats['today_blocked']}</b> ta\n\n"
        f"📈 <b>Umumiy ko'rsatkichlar:</b>\n"
        f"• Jami xabarlar: <b>{stats['total_messages']}</b> ta\n"
        f"• Ruxsat berilgan: <b>{stats['total_allowed']}</b> ta\n"
        f"• Bloklangan: <b>{stats['total_blocked']}</b> ta ({stats['block_rate']}%)\n"
        f"• Shikoyatlar: <b>{stats['total_reports']}</b> ta (Kutilmoqda: <b>{stats['pending_reports']}</b>)\n\n"
        f"🌐 <i>Batafsil boshqaruv va grafiklar Administrator panelida mavjud.</i>"
    )

    await message.reply(stats_text, parse_mode="HTML")


@admin_router.message(Command("ban"))
async def cmd_ban(message: types.Message, command: CommandObject, bot: Bot):
    """Foydalanuvchini bloklash (faqat adminlar uchun)"""
    if message.from_user.id != settings.ADMIN_TELEGRAM_ID:
        await message.reply("Sizda bu buyruqni bajarish huquqi yo'q.")
        return

    if not command.args:
        await message.reply("Foydalanuvchi Telegram ID sini kiriting: <code>/ban 12345678</code>", parse_mode="HTML")
        return

    try:
        target_id = int(command.args.strip())
        async with AsyncSessionLocal() as session:
            user = (await session.execute(select(User).where(User.telegram_id == target_id))).scalar_one_or_none()
            if user:
                user.is_banned = True
                await session.commit()
                await message.reply(f"✅ Foydalanuvchi {target_id} tizimda bloklandi.")
            else:
                await message.reply("Foydalanuvchi bazadan topilmadi.")
    except Exception as e:
        await message.reply(f"Xatolik: {e}")
