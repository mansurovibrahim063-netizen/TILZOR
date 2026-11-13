import json
import logging
import re
from dataclasses import dataclass
from typing import Optional, Dict, Any
import httpx
from config import settings

logger = logging.getLogger(__name__)


@dataclass
class GeminiCheckResult:
    is_violation: bool
    violation_type: str  # "NONE", "SPAM", "LINK", "INSULT", "CTA"
    toxicity_score: float  # 0.0 to 100.0
    reason: str
    translated_uz: str
    translated_ru: str


SYSTEM_PROMPT = """Sen ijtimoiy tarmoqlar va Telegram guruhlarida izohlar, fikr-mulohazalar va murojaatlarni tahlil qiluvchi professional AI-Moderatorsan.

Vazifalaring:
1. Xabarni chuqur tahlil qilish:
   - INSULT: Ochiq, yashirin, kinoyali, istehzoli yoki niqoblangan haqoratlar, kamsitish, tahqirlash.
   - SPAM: Tijoriy reklamalar, foydasiz takrorlar, keraksiz xabarlar.
   - CTA (Taqiqlangan chaqiriq): Foydalanuvchilarni tashqi platformalarga, boshqa guruh/kanallarga, shaxsiy yozishmaga (lichkaga), moliyaviy piramidalarga yoki shubhali harakatlarga yo'naltiruvchi chaqiriqlar ("lichkamga yozing", "profilimga kiring", "daromad toping", "obuna bo'ling").
   - LINK: Sayt, havola, domen yoki ularga ishoralar.
   - NONE: Qonuniy, odobli va qoidalarga mos xabar.
2. Xabarning umumiy toksiklik darajasini 0 dan 100 gacha (toxicity_score) belgilash. 0 - to'liq xavfsiz, 100 - o'ta zaharli/buzuq.
3. Avtomatik tarjima: Har bir xabarni o'zbek tiliga (uz) va rus tiliga (ru) to'liq va aniq tarjima qilish.

MUHIM: Javobni FAQAT toza JSON formatida qaytar, hech qanday qo'shimcha belgisiz (markdown ```json o'ramisiz):
{
  "is_violation": true yoki false,
  "violation_type": "NONE" | "SPAM" | "LINK" | "INSULT" | "CTA",
  "toxicity_score": 0 dan 100 gacha son,
  "reason": "Qoidabuzarlik sababi o'zbek tilida qisqa va lo'nda tushuntirish",
  "translated_uz": "Matnning o'zbekcha tarjimasi",
  "translated_ru": "Matnning ruscha tarjimasi"
}
"""


class GeminiModerator:
    def __init__(self):
        self.api_key = settings.GEMINI_API_KEY
        self.model = settings.GEMINI_MODEL or "gemini-2.5-flash"

    async def analyze_message(self, text: str) -> GeminiCheckResult:
        """Matnni Gemini AI orqali to'liq tekshirish va tarjima qilish"""
        if not text or not text.strip():
            return GeminiCheckResult(
                is_violation=False,
                violation_type="NONE",
                toxicity_score=0.0,
                reason="Bo'sh xabar",
                translated_uz="",
                translated_ru=""
            )

        # Agar API kalit ko'rsatilmagan bo'lsa, zaxira (fallback) aqlli tahlilchini ishlatamiz
        if not self.api_key or self.api_key.startswith("your-") or len(self.api_key) < 15:
            return self._fallback_local_analysis(text)

        # Gemini API ga so'rov yuborish
        try:
            return await self._call_gemini_api(text)
        except Exception as e:
            logger.error(f"Gemini API xatoligi: {e}")
            fallback_res = self._fallback_local_analysis(text)
            fallback_res.reason += f" (Gemini zaxira rejimi: {str(e)[:50]})"
            return fallback_res

    async def _call_gemini_api(self, text: str) -> GeminiCheckResult:
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{self.model}:generateContent?key={self.api_key}"
        
        prompt = f"{SYSTEM_PROMPT}\n\nTahlil qilinishi kerak bo'lgan xabar:\n\"\"\"{text}\"\"\""

        payload = {
            "contents": [
                {
                    "parts": [{"text": prompt}]
                }
            ],
            "generationConfig": {
                "temperature": 0.1,
                "response_mime_type": "application/json"
            }
        }

        async with httpx.AsyncClient(timeout=15.0) as client:
            response = await client.post(url, json=payload)
            response.raise_for_status()
            data = response.json()

        # Javobni parsing qilish
        candidate = data.get("candidates", [{}])[0]
        content_text = candidate.get("content", {}).get("parts", [{}])[0].get("text", "{}")

        # JSON tozalash (agar markdown backticklar qo'shilgan bo'lsa)
        content_text = re.sub(r'^```json\s*', '', content_text.strip(), flags=re.MULTILINE)
        content_text = re.sub(r'```$', '', content_text.strip())

        parsed = json.loads(content_text)

        is_viol = bool(parsed.get("is_violation", False))
        violation_type = str(parsed.get("violation_type", "NONE")).upper()
        toxicity_score = float(parsed.get("toxicity_score", 0.0))
        reason = str(parsed.get("reason", ""))
        translated_uz = str(parsed.get("translated_uz", text))
        translated_ru = str(parsed.get("translated_ru", text))

        # Agar toxicity_score belgilangan chegaradan yuqori bo'lsa, qoidabuzarlik deb baholanadi
        if toxicity_score >= settings.TOXICITY_THRESHOLD and not is_viol:
            is_viol = True
            if violation_type == "NONE":
                violation_type = "INSULT"
                reason = f"Yuqori toksiklik darajasi aniqlandi ({toxicity_score}%)"

        return GeminiCheckResult(
            is_violation=is_viol,
            violation_type=violation_type,
            toxicity_score=toxicity_score,
            reason=reason if reason else "Qoidabuzarlik aniqlandi",
            translated_uz=translated_uz,
            translated_ru=translated_ru
        )

    def _fallback_local_analysis(self, text: str) -> GeminiCheckResult:
        """API kalit bo'lmaganda yoki tarmoq uzilganda ishlaydigan evristik tahlilchi"""
        lower = text.lower()

        # CTA (Tashqi platformalarga, guruhlarga, lichkaga chaqiriqlar)
        cta_patterns = [
            r'lichka(?:ga|da|mga)?\s*(?:yoz|ot|o\'t|murojaat|bog\'lan)',
            r'profil(?:im|dagi)?\s*(?:ga|havola|link)',
            r'kanal(?:im)?(?:ga)?\s*obuna',
            r'(?:pul|daromad|invest|daromad)\s*(?:topish|ishlash|sarmoya)',
            r'kripto|binance|forex|signal(?:lar)?',
            r'(?:menejer|admin)\s*bilan\s*bog\'laning',
            r'пишите\s*в\s*личку',
            r'переходи\s*(?:по|в)',
            r'подпишись\s*на\s*канал'
        ]

        for pat in cta_patterns:
            if re.search(pat, lower):
                return GeminiCheckResult(
                    is_violation=True,
                    violation_type="CTA",
                    toxicity_score=75.0,
                    reason="Taqiqlangan chaqiriq (CTA): foydalanuvchini tashqi manbaga yoki shaxsiy yozishmaga undash.",
                    translated_uz=text,
                    translated_ru=text
                )

        # Yashirin haqorat va kamsitishlar (kinoya va istehzo belgilari)
        subtle_insult_patterns = [
            r'aqling\s*(?:yetmaydi|yoq|kam)',
            r'miyasi\s*yoq',
            r'savodsiz(?:lar)?',
            r'tushunmaydigan\s*ahmoq',
            r'molga\s*oxshaysan',
            r'eshak',
            r'тупой|дурак|идиот|дебил'
        ]

        for pat in subtle_insult_patterns:
            if re.search(pat, lower):
                return GeminiCheckResult(
                    is_violation=True,
                    violation_type="INSULT",
                    toxicity_score=80.0,
                    reason="Yashirin yoki kamsituvchi haqorat aniqlandi.",
                    translated_uz=text,
                    translated_ru=text
                )

        # Reklama va spam belgilari
        spam_keywords = ['aksiya', 'skidka', 'arzon narxda', 'sotiladi', 'buyurtma bering', 'скидка', 'акция', 'распродажа']
        if any(kw in lower for kw in spam_keywords):
            return GeminiCheckResult(
                is_violation=True,
                violation_type="SPAM",
                toxicity_score=60.0,
                reason="Tijoriy reklama yoki spam xabari.",
                translated_uz=text,
                translated_ru=text
            )

        return GeminiCheckResult(
            is_violation=False,
            violation_type="NONE",
            toxicity_score=5.0,
            reason="Xabar qoidalar doirasida",
            translated_uz=text,
            translated_ru=text
        )
