import re
import time
from collections import defaultdict
from dataclasses import dataclass
from typing import Optional, Tuple, Dict, List
from config import settings


@dataclass
class RegexCheckResult:
    is_violation: bool
    violation_type: str  # "LINK", "SPAM", "INSULT", "FLOOD", "NONE"
    reason: str
    matched_text: Optional[str] = None


class RegexEngine:
    # URL va Telegram havolalari uchun qoliplar
    URL_PATTERNS = [
        # Standart URL lar (http, https, www)
        re.compile(r'https?://(?:www\.)?[-a-zA-Z0-9@:%._+~#=]{1,256}\.[a-zA-Z0-9()]{1,6}\b(?:[-a-zA-Z0-9()@:%_+.~#?&/=]*)', re.IGNORECASE),
        re.compile(r'www\.[-a-zA-Z0-9@:%._+~#=]{1,256}\.[a-zA-Z0-9()]{1,6}\b(?:[-a-zA-Z0-9()@:%_+.~#?&/=]*)', re.IGNORECASE),
        
        # Telegram havolalari (t.me, telegram.me, telegram.dog)
        re.compile(r'(?:https?://)?(?:www\.)?(?:t\.me|telegram\.me|telegram\.dog)/(?:joinchat/)?[a-zA-Z0-9_+/-]+', re.IGNORECASE),
        re.compile(r'(?:https?://)?(?:www\.)?t\.me/\+[a-zA-Z0-9_-]+', re.IGNORECASE),
        
        # Niqoblangan havolalar (masalan: sayt[dot]uz, sayt (dot) com, kanal . t . me)
        re.compile(r'[a-zA-Z0-9\-_]{2,}\s*(?:\[dot\]|\(dot\)|\.\s+)\s*(?:com|uz|ru|org|net|io|me|info|biz|xyz|site|top|club|link|online|pro|shop)', re.IGNORECASE),
        
        # Markdown havolalar [matn](havola)
        re.compile(r'\[.*?\]\((https?://.*?|t\.me/.*?)\)', re.IGNORECASE)
    ]

    # Ochiq haqoratlar va so'kinishlar lug'ati (O'zbek va Rus tillaridagi asosiy ildizlar)
    PROFANITY_PATTERNS = [
        # O'zbekcha ochiq so'kinishlar (asosiy ildizlar va leetspeak)
        r'\b(?:onangni|onangdi|opangni|oyingni|amxona|ko\'t|kut|dalbayob|dalbayop|jalap|jalab|itvachcha|haromi|onangni\s+s|kotingga|sikaman|sike|sikish|sikay|qotoq|qo\'toq|ske)\b',
        # Ruscha so'kinishlar (mat)
        r'\b(?:хуй|хуя|хуе|пизд|блят|бляд|ебат|ебан|сука|гандон|гондон|пидор|пидар|мудак|чмо|шлюх|нах|нахуй)\w*\b'
    ]

    def __init__(self):
        self.profanity_regex = [re.compile(p, re.IGNORECASE | re.UNICODE) for p in self.PROFANITY_PATTERNS]
        # Flood va takroriy xabarlar xotirasi: {user_id: [(timestamp, text_hash)]}
        self._user_messages: Dict[int, List[Tuple[float, str]]] = defaultdict(list)

    def check_links(self, text: str) -> Optional[str]:
        """Barcha turdagi havolalarni tekshirish"""
        for pattern in self.URL_PATTERNS:
            match = pattern.search(text)
            if match:
                return match.group(0)
        return None

    def check_profanity(self, text: str) -> Optional[str]:
        """Ochiq haqoratlarni tekshirish"""
        for pattern in self.profanity_regex:
            match = pattern.search(text)
            if match:
                return match.group(0)
        return None

    def check_flood_and_repetition(self, user_id: int, text: str) -> Optional[str]:
        """Takroriy va flood xabarlarni aniqlash"""
        if not settings.ENABLE_FLOOD_PROTECTION:
            return None

        now = time.time()
        window = settings.FLOOD_WINDOW_SECONDS
        max_repeats = settings.FLOOD_MAX_IDENTICAL_MESSAGES

        # Eski xabarlarni tozalash
        history = [entry for entry in self._user_messages[user_id] if now - entry[0] <= window]
        self._user_messages[user_id] = history

        # Matnni normallashtirish
        clean_text = re.sub(r'\s+', ' ', text.strip().lower())
        
        # Oxirgi o'xshash xabarlar sonini hisoblash
        identical_count = sum(1 for _, old_text in history if old_text == clean_text)

        # Yangi xabarni qo'shish
        self._user_messages[user_id].append((now, clean_text))

        if identical_count >= max_repeats and len(clean_text) > 4:
            return f"Takroriy xabar: oxirgi {window} soniyada {identical_count + 1} marta yuborildi."

        return None

    def evaluate(self, user_id: int, text: str) -> RegexCheckResult:
        """1-bosqich: To'liq Regex va evristik tekshiruv"""
        if not text or not text.strip():
            return RegexCheckResult(is_violation=False, violation_type="NONE", reason="Bo'sh xabar")

        # 1. Havolalarni tekshirish
        if settings.STRICT_LINK_BLOCKING:
            link_match = self.check_links(text)
            if link_match:
                return RegexCheckResult(
                    is_violation=True,
                    violation_type="LINK",
                    reason="Taqiqlangan havola yoki Telegram kanali manzili aniqlandi.",
                    matched_text=link_match
                )

        # 2. Ochiq haqoratlarni tekshirish
        profanity_match = self.check_profanity(text)
        if profanity_match:
            return RegexCheckResult(
                is_violation=True,
                violation_type="INSULT",
                reason="Xabarda ochiq so'kinish yoki haqoratli so'z aniqlandi.",
                matched_text=profanity_match
            )

        # 3. Flood va takroriy xabarlar
        flood_reason = self.check_flood_and_repetition(user_id, text)
        if flood_reason:
            return RegexCheckResult(
                is_violation=True,
                violation_type="SPAM",
                reason=flood_reason,
                matched_text=None
            )

        return RegexCheckResult(is_violation=False, violation_type="NONE", reason="1-bosqichdan toza o'tdi")
