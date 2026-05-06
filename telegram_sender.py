import logging
import requests
from config import BOT_TOKEN, CHANNEL_USERNAME, REQUEST_TIMEOUT

logger = logging.getLogger(__name__)

TELEGRAM_API_BASE = "https://api.telegram.org/bot{token}/{method}"


def _api_url(method: str) -> str:
    return TELEGRAM_API_BASE.format(token=BOT_TOKEN, method=method)


def _build_inline_keyboard(product_url: str) -> dict:
    return {
        "inline_keyboard": [
            [
                {
                    "text": "🛒 להזמנה באתר",
                    "url": product_url,
                }
            ]
        ]
    }


def send_product(product: dict, caption: str) -> bool:
    """
    Send a product post to the Telegram channel.
    Returns True on success, False on failure.
    """
    if not BOT_TOKEN:
        logger.error("BOT_TOKEN is not set. Cannot send to Telegram.")
        return False

    channel = CHANNEL_USERNAME
    image_url = product.get("product_image", "")
    product_url = product.get("product_url", "")
    keyboard = _build_inline_keyboard(product_url)

    if image_url:
        return _send_photo(channel, image_url, caption, keyboard)
    else:
        return _send_message(channel, caption, keyboard)


def _send_photo(channel: str, photo_url: str, caption: str, keyboard: dict) -> bool:
    """Send a photo with caption to Telegram."""
    payload = {
        "chat_id": channel,
        "photo": photo_url,
        "caption": caption,
        "parse_mode": "HTML",
        "reply_markup": keyboard,
    }
    try:
        resp = requests.post(
            _api_url("sendPhoto"),
            json=payload,
            timeout=REQUEST_TIMEOUT,
        )
        data = resp.json()
        if data.get("ok"):
            logger.info("Photo sent successfully to %s", channel)
            return True
        else:
            logger.error(
                "Telegram sendPhoto error: %s – falling back to text.",
                data.get("description"),
            )
            # Fallback: send without image
            return _send_message(channel, caption, keyboard)
    except Exception as e:
        logger.error("Exception during sendPhoto: %s", e)
        return False


def _send_message(channel: str, text: str, keyboard: dict) -> bool:
    """Send a text-only message to Telegram."""
    payload = {
        "chat_id": channel,
        "text": text,
        "parse_mode": "HTML",
        "reply_markup": keyboard,
        "disable_web_page_preview": False,
    }
    try:
        resp = requests.post(
            _api_url("sendMessage"),
            json=payload,
            timeout=REQUEST_TIMEOUT,
        )
        data = resp.json()
        if data.get("ok"):
            logger.info("Message sent successfully to %s", channel)
            return True
        else:
            logger.error(
                "Telegram sendMessage error: %s",
                data.get("description"),
            )
            return False
    except Exception as e:
        logger.error("Exception during sendMessage: %s", e)
        return False


def test_connection() -> bool:
    """Test that the bot token is valid by calling getMe."""
    if not BOT_TOKEN:
        logger.error("BOT_TOKEN is not set.")
        return False
    try:
        resp = requests.get(_api_url("getMe"), timeout=REQUEST_TIMEOUT)
        data = resp.json()
        if data.get("ok"):
            bot = data["result"]
            logger.info("Bot connected: @%s (%s)", bot["username"], bot["first_name"])
            return True
        else:
            logger.error("getMe failed: %s", data.get("description"))
            return False
    except Exception as e:
        logger.error("Exception during getMe: %s", e)
        return False
