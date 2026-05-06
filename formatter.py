import html
import logging

logger = logging.getLogger(__name__)

TELEGRAM_CAPTION_LIMIT = 1024
TELEGRAM_MESSAGE_LIMIT = 4096


def _escape(text: str) -> str:
    """Escape HTML special characters for Telegram HTML parse mode."""
    return html.escape(text or "", quote=False)


def format_post(product: dict) -> str:
    """
    Build a Hebrew marketing post for Telegram.
    Returns an HTML-formatted string.
    """
    name = _escape(product.get("product_name", ""))
    url = product.get("product_url", "")
    price = _escape(product.get("price", ""))
    sale_price = _escape(product.get("sale_price", ""))
    description = _escape(product.get("description", ""))
    specs: list[str] = product.get("specs", [])
    availability = _escape(product.get("availability", ""))

    lines: list[str] = []

    # Header
    lines.append("🔥 <b>מוצר מומלץ מקומפס גריל</b>")
    lines.append("")

    # Product name
    lines.append(f"<b>{name}</b>")
    lines.append("")

    # Short description (max 200 chars)
    if description:
        short_desc = description[:200].strip()
        if len(description) > 200:
            short_desc += "..."
        lines.append(short_desc)
        lines.append("")

    # Price block
    if sale_price:
        lines.append(f"🔥 <b>מחיר מבצע: {sale_price}</b>")
        if price:
            lines.append(f"<s>מחיר מקורי: {price}</s>")
    elif price:
        lines.append(f"💰 <b>מחיר: {price}</b>")
    else:
        lines.append("💰 לפרטים ומחיר עדכני <a href=\"{}\">באתר</a>".format(url))

    lines.append("")

    # Specs / bullet points (max 3)
    if specs:
        for spec in specs[:3]:
            lines.append(f"✅ {_escape(spec)}")
        lines.append("")

    # Availability
    if availability and "out" not in availability.lower():
        lines.append(f"📦 {availability}")
        lines.append("")

    # CTA link
    lines.append(f'🛒 <a href="{url}">לצפייה והזמנה באתר</a>')
    lines.append("")

    # Footer
    lines.append("🚚 <i>משלוחים לכל הארץ</i>")
    lines.append("<i>*עד גמר המלאי | המחיר הקובע הוא המחיר באתר</i>")

    text = "\n".join(lines)

    # Ensure we don't exceed Telegram limits
    if len(text) > TELEGRAM_CAPTION_LIMIT:
        # Trim description and rebuild
        logger.warning("Post text too long (%d chars), trimming description.", len(text))
        if description and len(description) > 50:
            product_copy = dict(product)
            product_copy["description"] = description[:80]
            return format_post(product_copy)
        else:
            text = text[:TELEGRAM_CAPTION_LIMIT]

    return text
