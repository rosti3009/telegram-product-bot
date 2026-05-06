# 🔥 Compass Grill Telegram Bot

בוט אוטומטי שמפרסם מוצרים מאתר [Compass Grill](https://compassgrill.co.il) לערוץ טלגרם.

---

## 📁 מבנה הפרויקט

```
telegram-product-bot/
├── main.py              # FastAPI app + endpoints
├── scraper.py           # שליפת מוצרים מהאתר
├── telegram_sender.py   # שליחה לטלגרם
├── scheduler.py         # תזמון אוטומטי
├── database.py          # SQLite – מניעת כפילויות
├── formatter.py         # בניית טקסט הפוסט
├── config.py            # קריאת ENV variables
├── requirements.txt
├── render.yaml
├── .env.example
└── data/
    └── bot.db           # נוצר אוטומטית
```

---

## 🚀 התקנה מקומית

### 1. שכפול הפרויקט

```bash
git clone <your-repo-url>
cd telegram-product-bot
```

### 2. יצירת סביבה וירטואלית (מומלץ)

```bash
python -m venv venv
source venv/bin/activate      # Linux/Mac
venv\Scripts\activate         # Windows
```

### 3. התקנת ספריות

```bash
pip install -r requirements.txt
```

### 4. הגדרת קובץ .env

```bash
cp .env.example .env
```

ערוך את `.env` והוסף את ה-BOT_TOKEN שלך:

```
BOT_TOKEN=123456789:ABCDefGhijklmnopqrSTUVwxyz
CHANNEL_USERNAME=@compassgrill
```

---

## ▶️ הרצה מקומית

```bash
uvicorn main:app --reload
```

הבוט ירוץ על `http://localhost:8000`

---

## 🧪 בדיקות

### בדיקת health

```bash
curl http://localhost:8000/health
```

תשובה תקינה:
```json
{"status": "ok", "bot_token_set": true, "channel": "@compassgrill"}
```

### שליחת מוצר ידנית לבדיקה

```bash
curl -X POST http://localhost:8000/send-random-product
```

זה יבחר מוצר רנדומלי, יסרוק אותו מהאתר וישלח לערוץ הטלגרם.

---

## ☁️ פריסה ב-Render

### 1. יצירת Web Service חדש ב-Render

1. היכנס ל-[Render Dashboard](https://dashboard.render.com)
2. לחץ **New → Web Service**
3. חבר את ה-GitHub repository שלך
4. הגדר:
   - **Build Command:** `pip install -r requirements.txt`
   - **Start Command:** `uvicorn main:app --host 0.0.0.0 --port $PORT`

### 2. הוספת Environment Variables ב-Render

תחת **Environment**, הוסף את המשתנים הבאים:

| משתנה | ערך לדוגמה |
|-------|------------|
| `BOT_TOKEN` | הטוקן מ-BotFather |
| `CHANNEL_USERNAME` | `@compassgrill` |
| `SITE_BASE_URL` | `https://compassgrill.co.il` |
| `CATEGORY_URLS` | `https://compassgrill.co.il/fuel-wood-smoking-pellets-charcoal/` |
| `POST_TIMES` | `10:00,14:00,19:30` |
| `TIMEZONE` | `Asia/Jerusalem` |
| `DB_PATH` | `data/bot.db` |
| `DAYS_BEFORE_REPEAT` | `14` |

### 3. הוספת Disk (חשוב!)

כדי ש-SQLite ישמור נתונים בין deployments:
1. תחת **Disks**, לחץ **Add Disk**
2. הגדר:
   - **Name:** `bot-data`
   - **Mount Path:** `/opt/render/project/src/data`
   - **Size:** `1 GB`

---

## 🤖 הוספת הבוט כמנהל בערוץ טלגרם

1. פתח את הערוץ `@compassgrill` בטלגרם
2. לחץ על שם הערוץ → **Administrators** → **Add Administrator**
3. חפש את שם הבוט: `@CompassGrillBot`
4. הוסף עם הרשאות:
   - ✅ **Post Messages**
   - שאר ההרשאות אינן נדרשות

---

## ➕ הוספת קטגוריות נוספות

ב-`.env` או ב-Render Environment Variables, עדכן את `CATEGORY_URLS`:

```
CATEGORY_URLS=https://compassgrill.co.il/fuel-wood-smoking-pellets-charcoal/,https://compassgrill.co.il/grills/,https://compassgrill.co.il/accessories/
```

הוסף קטגוריות מופרדות בפסיק.

---

## 🔍 מציאת Chat ID אם הערוץ לא עובד עם @username

לפעמים טלגרם מחייב שימוש ב-Chat ID מספרי (כמו `-100123456789`) במקום `@username`.

### שיטה 1 – דרך הדפדפן

1. פתח `https://web.telegram.org`
2. לחץ על הערוץ שלך
3. ה-URL ייראה כך: `https://web.telegram.org/z/#-1001234567890`
4. ה-Chat ID הוא: `-100` + המספר בסוף → למשל `-1001234567890`

### שיטה 2 – דרך ה-Bot

1. שלח הודעה לערוץ כמנהל
2. גש ל-URL הבא בדפדפן:
```
https://api.telegram.org/bot<BOT_TOKEN>/getUpdates
```
3. חפש בתוצאה את `"chat": {"id": ...}` – זה ה-Chat ID שלך.

### שיטה 3 – בוט עזר

שלח `/start` ל-[@username_to_id_bot](https://t.me/username_to_id_bot) ושלח לו את שם הערוץ.

לאחר שמצאת את ה-Chat ID, עדכן ב-.env:
```
CHANNEL_USERNAME=-1001234567890
```

---

## 🧠 תוספת AI בעתיד

הקוד בנוי כך שניתן בקלות להוסיף ניסוח AI לפוסטים:

1. ב-`formatter.py`, הוסף קריאה ל-OpenAI / Anthropic API
2. שלח את נתוני המוצר ובקש מ-AI לנסח את הפוסט
3. החזר את הטקסט המנוסח כ-`caption`

```python
# דוגמה עתידית ב-formatter.py
import openai

def format_post_with_ai(product: dict) -> str:
    prompt = f"כתוב פוסט שיווקי קצר בעברית למוצר: {product['product_name']}..."
    response = openai.chat.completions.create(model="gpt-4", messages=[...])
    return response.choices[0].message.content
```

---

## 📋 מידע נוסף

- הפוסטים נשלחים בשעות: 10:00, 14:00, 19:30 (שעון ישראל)
- כל מוצר לא יפורסם שוב ב-14 ימים הקרובים
- אם כל המוצרים פורסמו, המחזור מתאפס אוטומטית
- לוגים מלאים זמינים ב-Render → Logs
