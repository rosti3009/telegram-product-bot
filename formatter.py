import html
import logging
import re

logger = logging.getLogger(__name__)

TELEGRAM_CAPTION_LIMIT = 1024
TELEGRAM_MESSAGE_LIMIT = 4096


def _escape(text: str) -> str:
    """Escape HTML special characters for Telegram HTML parse mode."""
    return html.escape(str(text or ""), quote=False)


def _clean_price(price: str) -> str:
    """
    Normalize price string.
    """
    if not price:
        return ""

    return (
        str(price)
        .replace("₪", "")
        .replace(",", "")
        .strip()
    )


def _is_zero_price(price: str) -> bool:
    """
    Detect invalid/zero prices from iStore.
    """
    cleaned = _clean_price(price)

    if not cleaned:
        return True

    return cleaned in {
        "0",
        "0.0",
        "0.00",
        "0.000",
    }


def _short_description(description: str, max_len: int = 220) -> str:
    """
    Create clean shortened description.
    """
    if not description:
        return ""

    text = re.sub(r"\s+", " ", description).strip()

    if len(text) <= max_len:
        return text

    return text[:max_len].rstrip() + "..."


def format_post(product: dict) -> str:
    """
    Build a professional Telegram marketing post.
    Returns HTML-formatted string.
    """

    name = _escape(product.get("product_name", ""))
    url = product.get("product_url", "")

    raw_price = product.get("price", "")
    raw_sale_price = product.get("sale_price", "")

    price = _escape(raw_price)
    sale_price = _escape(raw_sale_price)

    description = _short_description(
        _escape(product.get("description", ""))
    )

    specs: list[str] = product.get("specs", [])
    availability = _escape(product.get("availability", ""))

    lines: list[str] = []

    # ── Header ─────────────────────────────────────
    lines.append("🔥 <b>מוצר מומלץ מקומפס גריל</b>")
    lines.append("")

    # ── Product Name ───────────────────────────────
    lines.append(f"<b>{name}</b>")
    lines.append("")

    # ── Description ────────────────────────────────
    if description:
        lines.append(description)
        lines.append("")

    # ── Price Logic ────────────────────────────────
    price_is_zero = _is_zero_price(raw_price)
    sale_price_is_zero = _is_zero_price(raw_sale_price)

    # Case 1:
    # Only sale price exists -> treat as regular price
    if price_is_zero and not sale_price_is_zero:
        lines.append(f"💰 <b>מחיר: {sale_price}</b>")

    # Case 2:
    # Both prices valid -> show discount
    elif not price_is_zero and not sale_price_is_zero:
        lines.append(f"🔥 <b>מחיר מבצע: {sale_price}</b>")
        lines.append(f"<s>מחיר רגיל: {price}</s>")

    # Case 3:
    # Only regular price exists
    elif not price_is_zero:
        lines.append(f"💰 <b>מחיר: {price}</b>")

    # Case 4:
    # No valid price
    else:
        lines.append(
            f'💰 <a href="{url}"><b>לצפייה במחיר באתר</b></a>'
        )

    lines.append("")

    # ── Specs ──────────────────────────────────────
    clean_specs = []

    for spec in specs:
        spec_text = str(spec).strip()

        if not spec_text:
            continue

        # Skip obvious menu garbage
        if "גריל גז" in spec_text and len(spec_text) < 25:
            continue

        clean_specs.append(spec_text)

    for spec in clean_specs[:3]:
        lines.append(f"✅ {_escape(spec)}")

    if clean_specs:
        lines.append("")

    # ── Availability ───────────────────────────────
    availability_lower = availability.lower()

    if availability and not any(
        x in availability_lower
        for x in [
            "out",
            "אזל",
            "לא במלאי",
        ]
    ):
        lines.append(f"📦 {availability}")
        lines.append("")

    # ── CTA ────────────────────────────────────────
    lines.append(f'🛒 <a href="{url}"><b>לצפייה והזמנה באתר</b></a>')
    lines.append("")

    # ── Footer ─────────────────────────────────────
    lines.append("🚚 <i>משלוחים לכל הארץ</i>")
    lines.append("🔥 <i>מבחר ענק לגריל, עישון ובישול חוץ</i>")
    lines.append("")
    lines.append("<i>*המחיר הקובע הוא המחיר באתר | עד גמר המלאי</i>")

    text = "\n".join(lines)

    # ── Telegram Limit Protection ──────────────────
    if len(text) > TELEGRAM_CAPTION_LIMIT:
        logger.warning(
            "Post too long (%d chars), trimming...",
            len(text),
        )

        text = text[:TELEGRAM_CAPTION_LIMIT - 3] + "..."

    return text