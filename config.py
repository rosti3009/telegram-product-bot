import os
from dotenv import load_dotenv

load_dotenv()


def get_list_env(key: str, default: str) -> list[str]:
    raw = os.getenv(key, default)
    return [item.strip() for item in raw.split(",") if item.strip()]


# Telegram
BOT_TOKEN: str = os.getenv("BOT_TOKEN", "")
CHANNEL_USERNAME: str = os.getenv("CHANNEL_USERNAME", "@compassgrill")

# Site
SITE_BASE_URL: str = os.getenv("SITE_BASE_URL", "https://compassgrill.co.il")
CATEGORY_URLS: list[str] = get_list_env(
    "CATEGORY_URLS",
    "https://compassgrill.co.il/fuel-wood-smoking-pellets-charcoal/",
)

# Scheduler
POST_TIMES: list[str] = get_list_env("POST_TIMES", "10:00,14:00,19:30")
TIMEZONE: str = os.getenv("TIMEZONE", "Asia/Jerusalem")

# Database
DB_PATH: str = os.getenv("DB_PATH", "data/bot.db")
DAYS_BEFORE_REPEAT: int = int(os.getenv("DAYS_BEFORE_REPEAT", "14"))

# HTTP
REQUEST_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "he-IL,he;q=0.9,en-US;q=0.8,en;q=0.7",
}
REQUEST_TIMEOUT: int = 15
