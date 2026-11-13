# 🛡️ AI-Moderator — Sun'iy Intellekt Asosidagi Moderatsiya Tizimi

Foydalanuvchilar tomonidan yuboriladigan izohlar, fikr-mulohazalar va murojaatlarni avtomatik tekshiradigan, tahlil qiladigan hamda belgilangan qoidalarga muvofiq moderatsiya qiladigan to'liq siklli sun'iy intellekt tizimi.

---

## 🚀 Asosiy Imkoniyatlar va Vazifalari

1. **Spamdan himoyalash:**
   - Tijoriy reklamalar, foydasiz takrorlar va keraksiz xabarlarni aniqlash hamda tozalash.
   - Bir foydalanuvchi tomonidan qisqa vaqt ichida ketma-ket yuborilgan takroriy (flood) xabarlarni cheklash.

2. **Havolalarni qat'iy bloklash:**
   - Barcha turdagi URL manzillar (`http`, `https`, `www`).
   - Telegram havolalari (`t.me`, `telegram.me`, `telegram.dog`, kanalga taklif havolalari).
   - Niqoblangan domenlar (masalan: `sayt[dot]uz`, `sayt (dot) com`, `kanal . t . me`).
   - Markdown formatidagi yashirin havolalar (`[matn](havola)`).

3. **Haqoratlarni aniqlash:**
   - Ochiq so'kinishlar va haqoratli so'zlar (O'zbek va Rus tillarida).
   - Yashirin, kinoyali, istehzoli va kontekst ichiga yashirilgan kamsitishlar (Gemini AI orqali).

4. **Taqiqlangan chaqiriqlarni (CTA) aniqlash:**
   - Foydalanuvchilarni tashqi platformalarga, boshqa guruh/kanallarga, shaxsiy yozishmaga (lichkaga) undovchi chaqiriqlar ("lichkaga yozing", "profilimdagi havola", "daromad toping").
   - Moliyaviy piramidalar, shubhali investitsiyalar, soxta aksiyalar va firibgarlik signallari.

5. **Gemini AI orqali chuqur semantik tahlil:**
   - Xabarning maqsadi, ohangi va kontekstini tahlil qilish.
   - Har bir xabarga 0 dan 100 gacha bo'lgan **Toksiklik darajasi (Toxicity Score)** berish.

6. **2 Bosqichli Moderatsiya Quvuri (Pipeline):**
   - **1-bosqich (Regex & Evristika):** 0 ms kechikish va bepul resurs sarfi bilan havolalar, ochiq so'kinishlar va flood hujumlarini bir zumda to'xtatadi.
   - **2-bosqich (Gemini AI):** Birinchi bosqichdan o'tgan nozik xabarlarni chuqur tahlil qiladi (kinoya, chaqiriq, kontekst).

7. **Foydalanuvchilar shikoyatlari (Report tizimi):**
   - Guruh a'zolari nojo'ya xabarga reply qilib `/report [sabab]` yoki `/shikoyat` buyrug'i orqali shikoyat qoldirishi mumkin.
   - Shikoyatlar Administrator panelining navbatiga tushadi va ko'rib chiqiladi.

8. **Avtomatik tarjima (O'zbek va Rus tillariga):**
   - Qabul qilingan har bir xabar avtomatik ravishda o'zbek (`uz`) va rus (`ru`) tillariga tarjima qilinadi va ma'lumotlar bazasida saqlanadi.

9. **Zamonaviy Web Administrator Paneli:**
   - **Dashboard:** Asosiy KPI ko'rsatkichlari, oxirgi 7 kunlik faollik grafigi (Chart.js), qoidabuzarliklar ulushi (Doughnut chart) va moderatsiya bosqichlari taqsimoti.
   - **Xabarlar jurnali:** Barcha xabarlar jadvali, holat, bosqich va qoidabuzarlik bo'yicha filtrlar, qidiruv hamda tarjimalar bilan to'liq ko'rish modali.
   - **Shikoyatlar boshqaruvi:** Kelib tushgan shikoyatlarni bir tugma bilan tasdiqlash yoki rad etish.
   - **Test laboratoriyasi (Tester):** Ixtiyoriy matnni real vaqt rejimida 2 bosqichli testdan o'tkazish va tarjimalarni ko'rish.
   - **Sozlamalar:** Toksiklik chegarasi, havola bloklash, flood filtri va API kalitlarni boshqarish.

10. **Hisobot va Statistika:**
    - Kunlik, haftalik va oylik qayta ishlangan, ruxsat berilgan va bloklangan xabarlar tahlili.

---

## 📂 Loyiha Tuzilishi

```
telegram-ai-moderator/
├── bot/                       # Telegram Bot (Aiogram 3.x)
│   ├── handlers/
│   │   ├── admin.py           # Admin buyruqlari (/start, /check, /stats, /ban)
│   │   ├── moderation.py      # Guruh xabarlarini real vaqtda ushlash va o'chirish
│   │   └── reports.py         # /report va /shikoyat buyruqlari
│   └── main.py                # Bot runner va dispetcher
├── database/                  # Ma'lumotlar bazasi (SQLAlchemy + SQLite/Async)
│   ├── db.py                  # Dvigatel va sessiyalar
│   ├── models.py              # User, MessageLog, Report jadvallari
│   └── seed.py                # Sinov uchun namunaviy demo ma'lumotlar
├── moderation/                # Moderatsiya yadrosi
│   ├── regex_engine.py        # 1-bosqich: Regex va qoidalar
│   ├── ai_engine.py           # 2-bosqich: Gemini AI chuqur tahlili va tarjima
│   └── pipeline.py            # 2 bosqichli unifikatsiyalangan quvur
├── services/                  # Xizmatlar qatlami
│   ├── message_service.py     # Xabarlar, foydalanuvchilar va statistika
│   └── report_service.py      # Shikoyatlarni boshqarish
├── web/                       # FastAPI Web Administrator Paneli
│   ├── templates/             # Zamonaviy Tailwind CSS shablonlari
│   │   ├── base.html
│   │   ├── dashboard.html
│   │   ├── messages.html
│   │   ├── reports.html
│   │   ├── tester.html
│   │   ├── settings.html
│   │   └── login.html
│   ├── static/                # Statik resurslar
│   └── app.py                 # FastAPI marshrutlari va avtorizatsiya
├── tests/                     # Sinov testlari
│   ├── test_moderator.py      # Yadro va pipeline testlari
│   └── test_web.py            # Web panel marshrutlari testlari
├── config.py                  # Tizim konfiguratsiyasi (Pydantic Settings)
├── requirements.txt           # Kerakli Python kutubxonalari
├── run.py                     # Asosiy ishga tushirish skripti
└── .env                       # Muhit o'zgaruvchilari
```

---

## ⚙️ O'rnatish va Ishga Tushirish

### 1. Talablar
- Python 3.10 yoki undan yuqori versiya.

### 2. Kutubxonalarni o'rnatish
```bash
pip install -r requirements.txt
```

### 3. Konfiguratsiyani sozlash (`.env`)
`.env` faylini oching va parametrlarni belgilang:
```env
# Telegram Bot ma'lumotlari (@BotFather dan olingan)
BOT_TOKEN=123456789:ABCDEF...
ADMIN_TELEGRAM_ID=77788899

# Google Gemini API (Google AI Studio: https://aistudio.google.com/)
GEMINI_API_KEY=AIzaSy...
GEMINI_MODEL=gemini-2.5-flash

# Web Admin Panel sozlamalari
WEB_HOST=127.0.0.1
WEB_PORT=8000
ADMIN_PASSWORD=admin123
SECRET_KEY=super-secret-key-change-me

# Moderatsiya parametrlari
TOXICITY_THRESHOLD=65
STRICT_LINK_BLOCKING=True
ENABLE_FLOOD_PROTECTION=True
AUTO_TRANSLATE=True
```

### 4. Tizimni ishga tushirish

**Ham Web Panel, ham Telegram Botni bir vaqtda ishga tushirish:**
```bash
python run.py
```

**Faqat Web Admin Panelni ishga tushirish:**
```bash
python run.py --web-only
```

**Faqat Telegram Botni ishga tushirish:**
```bash
python run.py --bot-only
```

Ishga tushgach:
- Web Admin Panel: **http://127.0.0.1:8000**
- Standart admin paroli: **`admin123`**

---

## 🧪 Testlarni Ishga Tushirish

Tizimning barcha qismlari avtomatlashtirilgan testlar bilan qamrab olingan:
```bash
# 1. Moderatsiya yadrosi va pipeline testlari:
python tests/test_moderator.py

# 2. Web admin paneli va API testlari:
python tests/test_web.py
```

---

## 🤖 Telegram Bot Buyruqlari

- `/start` — Bot haqida to'liq ma'lumot va qo'llanma.
- `/check [matn]` — Istalgan matnni to'g'ridan-to'g'ri Telegram chatida 2 bosqichli AI tahlilidan o'tkazish va o'zbek/rus tarjimalarini ko'rish.
- `/stats` — Bugungi va umumiy moderatsiya statistikasi.
- `/report [sabab]` — Guruhda qoidabuzar xabarga reply qilib yuborilganda xabar ustidan shikoyat qoldirish.
- `/ban [user_id]` — Qoidabuzar foydalanuvchini moderator tomonidan bloklash.
