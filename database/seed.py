import asyncio
import os
import sys
from datetime import datetime, timedelta

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from database.db import AsyncSessionLocal, init_db
from database.models import User, MessageLog, Report


DEMO_MESSAGES = [
    {
        "sender": "Ali Valiyev", "username": "alivali", "tg_id": 1001,
        "text": "Assalomu alaykum barchaga! Guruh juda foydali ekan, yangi ma'lumotlar uchun rahmat.",
        "uz": "Assalomu alaykum barchaga! Guruh juda foydali ekan, yangi ma'lumotlar uchun rahmat.",
        "ru": "Здравствуйте всем! Группа очень полезная, спасибо за новую информацию.",
        "status": "ALLOWED", "stage": "CLEAN", "violation": "NONE", "score": 2.0, "reason": "Xabar odobli va qoidalarga mos."
    },
    {
        "sender": "Botirbek", "username": "botir_pro", "tg_id": 1002,
        "text": "Tezkor daromad olishni xohlaysizmi? Kuniga 200$ ishlash uchun darhol profilimga kiring yoki lichkamga yozing!",
        "uz": "Tezkor daromad olishni xohlaysizmi? Kuniga 200$ ishlash uchun darhol profilimga kiring yoki lichkamga yozing!",
        "ru": "Хотите быстрый заработок? Чтобы зарабатывать 200$ в день, срочно переходите в мой профиль или пишите в личку!",
        "status": "BLOCKED", "stage": "GEMINI", "violation": "CTA", "score": 85.0, "reason": "Taqiqlangan chaqiriq (CTA): foydalanuvchini shaxsiy yozishmaga undash va shubhali daromad."
    },
    {
        "sender": "SpamBot_77", "username": "spammer77", "tg_id": 1003,
        "text": "Bizning yangi kanalimizga obuna bo'ling: https://t.me/kripto_daromad_uz eng yaxshi signallar shu yerda!",
        "uz": "Bizning yangi kanalimizga obuna bo'ling: https://t.me/kripto_daromad_uz eng yaxshi signallar shu yerda!",
        "ru": "Подписывайтесь на наш новый канал: https://t.me/kripto_daromad_uz лучшие сигналы здесь!",
        "status": "BLOCKED", "stage": "REGEX", "violation": "LINK", "score": 60.0, "reason": "Taqiqlangan Telegram kanali havolasi aniqlandi."
    },
    {
        "sender": "Javohir", "username": "javohir_99", "tg_id": 1004,
        "text": "Sen umuman tushunmaydigan ahmoq ekansan, miyang yo'q savodsizsan.",
        "uz": "Sen umuman tushunmaydigan ahmoq ekansan, miyang yo'q savodsizsan.",
        "ru": "Ты вообще ничего не понимающий дурак, безмозглый и неграмотный.",
        "status": "BLOCKED", "stage": "GEMINI", "violation": "INSULT", "score": 92.0, "reason": "Kamsituvchi va haqoratli so'zlar aniqlandi."
    },
    {
        "sender": "Sardor", "username": "sardor_dev", "tg_id": 1005,
        "text": "Ertaga soat 15:00 da o'tkaziladigan vebinar bo'yicha kimda savollar bor?",
        "uz": "Ertaga soat 15:00 da o'tkaziladigan vebinar bo'yicha kimda savollar bor?",
        "ru": "У кого есть вопросы по завтрашнему вебинару в 15:00?",
        "status": "ALLOWED", "stage": "CLEAN", "violation": "NONE", "score": 1.0, "reason": "Qonuniy savol."
    },
    {
        "sender": "Marketuz", "username": "market_bot", "tg_id": 1006,
        "text": "ARZON NARXDA SMARTFONLAR! faqat bugun 50% skidka, shoshiling sotiladi!",
        "uz": "ARZON NARXDA SMARTFONLAR! faqat bugun 50% skidka, shoshiling sotiladi!",
        "ru": "СМАРТФОНЫ ПО ДЕШЕВОЙ ЦЕНЕ! только сегодня скидка 50%, спешите продается!",
        "status": "BLOCKED", "stage": "GEMINI", "violation": "SPAM", "score": 70.0, "reason": "Tijoriy reklama va spam."
    },
    {
        "sender": "Nodir", "username": "nodir_bek", "tg_id": 1007,
        "text": "Kutib turing, administratorlar hozir yordam berishadi.",
        "uz": "Kutib turing, administratorlar hozir yordam berishadi.",
        "ru": "Подождите, администраторы сейчас помогут.",
        "status": "ALLOWED", "stage": "CLEAN", "violation": "NONE", "score": 0.0, "reason": "Xavfsiz xabar."
    }
]


async def seed_demo_data():
    async with AsyncSessionLocal() as session:
        # Check if already seeded
        from sqlalchemy import select, func
        count = (await session.execute(select(func.count(MessageLog.id)))).scalar_one()
        if count > 0:
            return

        now = datetime.utcnow()
        for idx, item in enumerate(DEMO_MESSAGES):
            user = User(
                telegram_id=item["tg_id"],
                username=item["username"],
                full_name=item["sender"],
                warning_count=1 if item["status"] == "BLOCKED" else 0
            )
            session.add(user)
            await session.commit()
            await session.refresh(user)

            # Spread dates over last 5 days
            created_dt = now - timedelta(days=(idx % 5), hours=(idx * 2))

            msg = MessageLog(
                telegram_message_id=2000 + idx,
                chat_id=-100123456789,
                chat_title="IT & Dasturlash Jamiyati",
                user_id=user.id,
                user_telegram_id=user.telegram_id,
                sender_name=item["sender"],
                sender_username=item["username"],
                original_text=item["text"],
                translated_uz=item["uz"],
                translated_ru=item["ru"],
                status=item["status"],
                detection_stage=item["stage"],
                violation_type=item["violation"],
                toxicity_score=item["score"],
                reason=item["reason"],
                action_taken="DELETED" if item["status"] == "BLOCKED" else "NONE",
                created_at=created_dt
            )
            session.add(msg)
            await session.commit()
            await session.refresh(msg)

            # Agar bu shikoyat qilinishi kerak bo'lgan xabar bo'lsa
            if idx == 1:
                rep = Report(
                    message_id=msg.id,
                    reporter_telegram_id=9999,
                    reporter_name="Dilshod Karimov",
                    reason="Ushbu xabar moliyaviy firibgarlik va guruh a'zolarini aldashga qaratilgan",
                    status="PENDING",
                    created_at=now - timedelta(hours=3)
                )
                session.add(rep)

            if idx == 3:
                rep = Report(
                    message_id=msg.id,
                    reporter_telegram_id=8888,
                    reporter_name="Malika Rahimova",
                    reason="Shaxsiyatimga tegadigan haqoratli gaplar yozgan",
                    status="APPROVED",
                    created_at=now - timedelta(days=1),
                    resolved_at=now - timedelta(hours=10)
                )
                session.add(rep)

        await session.commit()


if __name__ == "__main__":
    async def main():
        await init_db()
        await seed_demo_data()
        print("Demo ma'lumotlar muvaffaqiyatli yuklandi.")
    asyncio.run(main())
