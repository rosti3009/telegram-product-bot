import logging
import random
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from pytz import timezone

from config import POST_TIMES, TIMEZONE
from scraper import fetch_all_product_links, scrape_product
from database import was_recently_posted, mark_as_posted, get_all_posted_urls, reset_cycle
from formatter import format_post
from telegram_sender import send_product

logger = logging.getLogger(__name__)

_scheduler: BackgroundScheduler | None = None

# In-memory cache of product URLs to avoid hitting the site on every post
_product_url_cache: list[str] = []


def _pick_unposted_product() -> dict | None:
    """
    Select a random product URL that hasn't been posted recently.
    Refreshes the cache if needed, resets cycle if all products are exhausted.
    """
    global _product_url_cache

    # Refresh cache if empty
    if not _product_url_cache:
        logger.info("Fetching product links from site...")
        _product_url_cache = fetch_all_product_links()
        if not _product_url_cache:
            logger.error("No product links found on the site.")
            return None

    # Shuffle for variety
    random.shuffle(_product_url_cache)

    for url in _product_url_cache:
        if not was_recently_posted(url):
            product = scrape_product(url)
            if product and product.get("product_name") and product.get("product_url"):
                return product
            else:
                logger.warning("Failed to scrape product at %s, skipping.", url)

    # All products recently posted – reset cycle
    logger.info("All products have been recently posted. Resetting cycle.")
    reset_cycle()
    _product_url_cache = fetch_all_product_links()
    random.shuffle(_product_url_cache)

    for url in _product_url_cache:
        product = scrape_product(url)
        if product and product.get("product_name"):
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
            _scheduler.add_job(post_product_job, trigger=trigger, id=f"post_{time_str}")
            logger.info("Scheduled post at %s %s", time_str, TIMEZONE)
        except (ValueError, Exception) as e:
            logger.error("Invalid POST_TIME '%s': %s", time_str, e)

    _scheduler.start()
    logger.info("Scheduler started with %d job(s).", len(_scheduler.get_jobs()))


def stop_scheduler() -> None:
    """Stop the scheduler gracefully."""
    global _scheduler
    if _scheduler and _scheduler.running:
        _scheduler.shutdown(wait=False)
        logger.info("Scheduler stopped.")
