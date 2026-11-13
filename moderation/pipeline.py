import logging
from dataclasses import dataclass
from typing import Optional
from config import settings
from moderation.regex_engine import RegexEngine, RegexCheckResult
from moderation.ai_engine import GeminiModerator, GeminiCheckResult

logger = logging.getLogger(__name__)


@dataclass
class ModerationResult:
    is_violation: bool
    status: str  # "ALLOWED", "BLOCKED"
    detection_stage: str  # "REGEX", "GEMINI", "CLEAN"
    violation_type: str  # "NONE", "SPAM", "LINK", "INSULT", "CTA", "FLOOD"
    toxicity_score: float
    reason: str
    action_taken: str  # "NONE", "DELETED", "WARNED", "BANNED"
    translated_uz: str
    translated_ru: str


class ModerationPipeline:
    def __init__(self):
        self.regex_engine = RegexEngine()
        self.gemini_engine = GeminiModerator()

    async def evaluate_message(self, user_id: int, text: str) -> ModerationResult:
        """
        Ikki bosqichli to'liq moderatsiya:
        1-bosqich: Regex & Heuristics (Havola, ochiq haqorat, flood)
        2-bosqich: Gemini AI (Yashirin haqorat, CTA/chaqiriq, spam, kontekst, tarjima)
        """
        # 1-BOSQICH: REGEX VA EVRISTIKA
        regex_result: RegexCheckResult = self.regex_engine.evaluate(user_id=user_id, text=text)

        if regex_result.is_violation:
            logger.info(f"1-bosqich (Regex) qoidabuzarlik aniqladi: {regex_result.violation_type} - {regex_result.reason}")
            
            # Agar tarjima yoqilgan bo'lsa va Gemini mavjud bo'lsa, tarjima olishga harakat qilamiz
            uz_trans = text
            ru_trans = text
            if settings.AUTO_TRANSLATE:
                try:
                    ai_res = await self.gemini_engine.analyze_message(text)
                    uz_trans = ai_res.translated_uz or text
                    ru_trans = ai_res.translated_ru or text
                except Exception:
                    pass

            return ModerationResult(
                is_violation=True,
                status="BLOCKED",
                detection_stage="REGEX",
                violation_type=regex_result.violation_type,
                toxicity_score=90.0 if regex_result.violation_type == "INSULT" else 60.0,
                reason=regex_result.reason,
                action_taken="DELETED",
                translated_uz=uz_trans,
                translated_ru=ru_trans
            )

        # 2-BOSQICH: GEMINI AI CHUQUR TAHLIL VA TARJIMA
        logger.info("1-bosqichdan o'tdi. 2-bosqich (Gemini AI) chuqur tahlili boshlanmoqda...")
        ai_result: GeminiCheckResult = await self.gemini_engine.analyze_message(text)

        if ai_result.is_violation:
            logger.info(f"2-bosqich (Gemini AI) qoidabuzarlik aniqladi: {ai_result.violation_type} - {ai_result.reason}")
            return ModerationResult(
                is_violation=True,
                status="BLOCKED",
                detection_stage="GEMINI",
                violation_type=ai_result.violation_type,
                toxicity_score=ai_result.toxicity_score,
                reason=ai_result.reason,
                action_taken="DELETED",
                translated_uz=ai_result.translated_uz,
                translated_ru=ai_result.translated_ru
            )

        # Xabar toza va qoidalarga to'liq mos keladi
        return ModerationResult(
            is_violation=False,
            status="ALLOWED",
            detection_stage="CLEAN",
            violation_type="NONE",
            toxicity_score=ai_result.toxicity_score,
            reason="Xabar belgilangan qoidalarga to'liq mos keladi.",
            action_taken="NONE",
            translated_uz=ai_result.translated_uz,
            translated_ru=ai_result.translated_ru
        )


pipeline = ModerationPipeline()
