import asyncio
import os
import sys

# Loyiha ildiz yo'lini qo'shish
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from moderation.regex_engine import RegexEngine
from moderation.ai_engine import GeminiModerator
from moderation.pipeline import ModerationPipeline
from database.db import init_db, AsyncSessionLocal
from services.message_service import MessageService
from services.report_service import ReportService


async def run_tests():
    print("=" * 60)
    print("AI-MODERATOR TESTLARINI O'TKAZISH")
    print("=" * 60)

    # 1. REGEX ENGINE TESTLARI
    print("\n[TEST 1] Regex Engine Havolalar va So'kinishlar:")
    regex = RegexEngine()

    test_link = "Mening kanalimga kiring: https://t.me/super_invest va sayt[dot]uz"
    res_link = regex.evaluate(user_id=1, text=test_link)
    print(f"  Havola testi: is_violation={res_link.is_violation}, type={res_link.violation_type}, matched={res_link.matched_text}")
    assert res_link.is_violation is True
    assert res_link.violation_type == "LINK"

    test_clean = "Assalomu alaykum, loyihangiz juda yoqdi!"
    res_clean = regex.evaluate(user_id=2, text=test_clean)
    print(f"  Toza matn testi: is_violation={res_clean.is_violation}, type={res_clean.violation_type}")
    assert res_clean.is_violation is False

    # 2. GEMINI AI / FALLBACK ENGINE TESTLARI
    print("\n[TEST 2] Gemini AI / Semantik Tahlil (CTA va Yashirin Haqorat):")
    ai_mod = GeminiModerator()

    test_cta = "Kuniga 200$ daromad topishni xohlasangiz hoziroq lichkamga yozing!"
    res_cta = await ai_mod.analyze_message(test_cta)
    print(f"  CTA testi: is_violation={res_cta.is_violation}, type={res_cta.violation_type}, reason={res_cta.reason}")
    assert res_cta.is_violation is True
    assert res_cta.violation_type == "CTA"

    test_subtle = "Sening miyang yo'q savodsizsan, gapni tushunmaysan"
    res_subtle = await ai_mod.analyze_message(test_subtle)
    print(f"  Yashirin haqorat: is_violation={res_subtle.is_violation}, type={res_subtle.violation_type}, score={res_subtle.toxicity_score}%")
    assert res_subtle.is_violation is True
    assert res_subtle.violation_type == "INSULT"

    # 3. 2 BOSQICHLI PIPELINE TESTI
    print("\n[TEST 3] 2-Bosqichli Birlashtirilgan Pipeline:")
    pipeline = ModerationPipeline()

    res_pipe1 = await pipeline.evaluate_message(user_id=10, text="https://t.me/scam_group kir")
    print(f"  Pipeline 1-bosqich: stage={res_pipe1.detection_stage}, status={res_pipe1.status}, type={res_pipe1.violation_type}")
    assert res_pipe1.detection_stage == "REGEX"
    assert res_pipe1.status == "BLOCKED"

    res_pipe2 = await pipeline.evaluate_message(user_id=11, text="Daromad ishlash uchun profilimga kiring")
    print(f"  Pipeline 2-bosqich: stage={res_pipe2.detection_stage}, status={res_pipe2.status}, type={res_pipe2.violation_type}")
    assert res_pipe2.detection_stage == "GEMINI"
    assert res_pipe2.status == "BLOCKED"

    res_pipe3 = await pipeline.evaluate_message(user_id=12, text="Bugungi dars soat nechada boshlanadi?")
    print(f"  Pipeline toza xabar: stage={res_pipe3.detection_stage}, status={res_pipe3.status}, uz_trans='{res_pipe3.translated_uz}'")
    assert res_pipe3.status == "ALLOWED"

    # 4. DATABASE VA XIZMATLAR TESTI
    print("\n[TEST 4] Ma'lumotlar bazasi va hisobotlar:")
    await init_db()
    async with AsyncSessionLocal() as session:
        # Xabarni qayd qilish
        msg = await MessageService.log_message(
            db=session,
            telegram_message_id=99991,
            chat_id=-100555,
            chat_title="Test Chat",
            user_telegram_id=777,
            sender_name="Test User",
            sender_username="testuser",
            original_text="Lichkamga yozing pul ishlaysiz",
            result=res_pipe2
        )
        print(f"  Xabar saqlandi: id={msg.id}, status={msg.status}, action={msg.action_taken}")
        assert msg.id is not None

        # Shikoyat qoldirish
        rep = await ReportService.create_report(
            db=session,
            message_id=msg.id,
            reporter_telegram_id=888,
            reporter_name="Nazoratchi",
            reason="Guruhda pul ishlashga chaqiryapti"
        )
        print(f"  Shikoyat saqlandi: id={rep.id}, status={rep.status}")
        assert rep.id is not None

        # Statistikani hisoblash
        stats = await MessageService.get_statistics(session)
        print(f"  Statistika: Total={stats['total_messages']}, Blocked={stats['total_blocked']}, Reports={stats['total_reports']}")
        assert stats["total_messages"] > 0

    print("\n" + "=" * 60)
    print("✅ BARCHA TESTLAR MUVAFFAQIYATLI O'TDI!")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(run_tests())
