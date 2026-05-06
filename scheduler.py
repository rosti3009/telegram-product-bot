import logging
import random
from urllib.parse import urlparse

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from pytz import timezone

from config import POST_TIMES, TIMEZONE
from scraper import fetch_all_product_links, scrape_product
from database import was_recently_posted, mark_as_posted, reset_cycle
from formatter import format_post
from telegram_sender import send_product

try:
    from category_weights import CATEGORY_WEIGHTS
except ImportError:
    CATEGORY_WEIGHTS = {}

logger = logging.getLogger(__name__)

_scheduler: BackgroundScheduler | None = None

# Cache product URLs to avoid hitting the site on every post
_product_url_cache: list[str] = []


def _get_category_key_from_url(url: str) -> str:
    """
    Extract first URL path segment as category key.
    Example:
    https://compassgrill.co.il/fuel-wood-smoking-pellets-charcoal/pecan-wood-chips/
    -> fuel-wood-smoking-pellets-charcoal
    """
    path_parts = [p for p in urlparse(url).path.strip("/").split("/") if p]
    return path_parts[0] if path_parts else ""


def _choose_weighted_category() -> str | None:
    """
    Choose category key based on CATEGORY_WEIGHTS.
    Example:
    {"grill-accessories": 40, "gas-grills": 20}
    """
    if not CATEGORY_WEIGHTS:
        return None

    categories = list(CATEGORY_WEIGHTS.keys())
    weights = list(CATEGORY_WEIGHTS.values())

    if not categories or sum(weights) <= 0:
        return None

    return random.choices(categories, weights=weights, k=1)[0]


def _refresh_product_cache() -> bool:
    global _product_url_cache

    logger.info("Fetching product links from site...")
    _product_url_cache = fetch_all_product_links()

    if not _product_url_cache:
        logger.error("No product links found on the site.")
        return False

    logger.info("Product cache loaded with %d URLs.", len(_product_url_cache))
    return True


def _find_valid_product_from_urls(urls: list[str]) -> dict | None:
    """
    Find first valid unposted product from a shuffled URL list.
    """
    random.shuffle(urls)

    for url in urls:
        if was_recently_posted(url):
            continue

        product = scrape_product(url)

        if product and product.get("product_name") and product.get("product_url"):
            return product

        logger.warning("Failed to scrape product at %s, skipping.", url)

    return None


def _pick_unposted_product() -> dict | None:
    """
    Pick product by category weights first.
    Fallback to all products if selected category has no available product.
    """
    global _product_url_cache

    if not _product_url_cache:
        if not _refresh_product_cache():
            return None

    selected_category = _choose_weighted_category()

    if selected_category:
        category_urls = [
            url for url in _product_url_cache
            if _get_category_key_from_url(url) == selected_category
        ]

        logger.info(
            "Selected weighted category: %s | products in category: %d",
            selected_category,
            len(category_urls),
        )

        product = _find_valid_product_from_urls(category_urls)

        if product:
            return product

        logger.warning(
            "No valid unposted product found in weighted category '%s'. Falling back to all products.",
            selected_category,
        )

    product = _find_valid_product_from_urls(_product_url_cache)

    if product:
        return product

    logger.info("All products have been recently posted. Resetting cycle.")
    reset_cycle()

    if not _refresh_product_cache():
        return None

    selected_category = _choose_weighted_category()

    if selected_category:
        category_urls = [
            url for url in _product_url_cache
            if _get_category_key_from_url(url) == selected_category
        ]

        product = _find_valid_product_from_urls(category_urls)

        if product:
            return product

    product = _find_valid_product_from_urls(_product_url_cache)

    if product:
        return product

    logger.error("Could not find any valid product to post after cycle reset.")
    return None


def post_product_job() -> bool:
    """Main job: pick a product, format it, send it to Telegram."""
    logger.info("Running scheduled post job...")

    product = _pick_unposted_product()

    if not product:
        logger.error("No product available to post.")
        return False

    caption = format_post(product)
    success = send_product(product, caption)

    if success:
        mark_as_posted(product["product_url"], product["product_name"])
        logger.info("Posted: %s", product["product_name"])
    else:
        logger.error("Failed to post: %s", product["product_name"])

    return success


def start_scheduler() -> None:
    """Start the APScheduler with configured POST_TIMES."""
    global _scheduler

    tz = timezone(TIMEZONE)
    _scheduler = BackgroundScheduler(timezone=tz)

    if not POST_TIMES:
        logger.warning("No POST_TIMES configured, scheduler will not run.")
        return

    for time_str in POST_TIMES:
        try:
            hour, minute = time_str.strip().split(":")
            trigger = CronTrigger(hour=int(hour), minute=int(minute), timezone=tz)
            _scheduler.add_job(
                post_product_job,
                trigger=trigger,
                id=f"post_{time_str}",
                replace_existing=True,
            )
            logger.info("Scheduled post at %s %s", time_str, TIMEZONE)

        except Exception as e:
            logger.error("Invalid POST_TIME '%s': %s", time_str, e)

    _scheduler.start()
    logger.info("Scheduler started with %d job(s).", len(_scheduler.get_jobs()))


def stop_scheduler() -> None:
    """Stop the scheduler gracefully."""
    global _scheduler

    if _scheduler and _scheduler.running:
        _scheduler.shutdown(wait=False)
        logger.info("Scheduler stopped.")