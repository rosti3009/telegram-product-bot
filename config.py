import os
from dotenv import load_dotenv

from categories import CATEGORY_URLS_DEFAULT

load_dotenv()


def get_list_env(key: str, default_items: list[str]) -> list[str]:
    """
    Reads comma-separated ENV variable.
    If ENV is empty, uses default_items from categories.py.
    """
    raw = os.getenv(key, "").strip()

    if not raw:
        return default_items

    return [item.strip() for item in raw.split(",") if item.strip()]


# Telegram
BOT_TOKEN: str = os.getenv("BOT_TOKEN", "").strip()
CHANNEL_USERNAME: str = os.getenv("CHANNEL_USERNAME", "@compassgrill").strip()

# Site
SITE_BASE_URL: str = os.getenv("SITE_BASE_URL", "https://compassgrill.co.il").strip()

CATEGORY_URLS: list[str] = get_list_env(
    "CATEGORY_URLS",
    CATEGORY_URLS_DEFAULT,
)

# Scheduler
POST_TIMES: list[str] = get_list_env(
    "POST_TIMES",
    ["09:00", "10:30", "12:00", "13:30", "15:00", "16:30", "18:00", "19:30", "21:00", "22:30"],
)

TIMEZONE: str = os.getenv("TIMEZONE", "Asia/Jerusalem").strip()

# Database
DB_PATH: str = os.getenv("DB_PATH", "data/bot.db").strip()
DAYS_BEFORE_REPEAT: int = int(os.getenv("DAYS_BEFORE_REPEAT", "3"))

# HTTP
REQUEST_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "he-IL,he;q=0.9,en-US;q=0.8,en;q=0.7",
}

REQUEST_TIMEOUT: int = int(os.getenv("REQUEST_TIMEOUT", "15"))