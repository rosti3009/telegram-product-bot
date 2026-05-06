import logging
import os
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse

from config import BOT_TOKEN, CHANNEL_USERNAME, POST_TIMES, TIMEZONE
from database import init_db
from scheduler import start_scheduler, stop_scheduler, post_product_job
from telegram_sender import test_connection

# ── Logging ────────────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)

logger = logging.getLogger(__name__)


# ── Lifespan ───────────────────────────────────────────────────────────────────
@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting Compass Grill Telegram Bot...")

    os.makedirs("data", exist_ok=True)
    init_db()

    if not BOT_TOKEN:
        logger.warning(
            "BOT_TOKEN is not set. Telegram posting will be disabled until it is set."
        )
    else:
        test_connection()

    start_scheduler()

    yield

    stop_scheduler()
    logger.info("Bot stopped.")


# ── App ────────────────────────────────────────────────────────────────────────
app = FastAPI(
    title="Compass Grill Telegram Bot",
    description="Automatically posts products from compassgrill.co.il to Telegram.",
    version="1.1.0",
    lifespan=lifespan,
)


# ── Endpoints ──────────────────────────────────────────────────────────────────
@app.get("/")
async def root():
    return JSONResponse(
        content={
            "status": "ok",
            "service": "Compass Grill Telegram Bot",
            "docs": "/docs",
            "health": "/health",
            "debug_products": "/debug/products",
        }
    )


@app.get("/health")
async def health_check():
    return JSONResponse(
        content={
            "status": "ok",
            "bot_token_set": bool(BOT_TOKEN),
            "channel": CHANNEL_USERNAME,
            "post_times": POST_TIMES,
            "timezone": TIMEZONE,
        }
    )


@app.get("/debug/products")
async def debug_products():
    """
    Checks product pulling without sending anything to Telegram.
    """
    try:
        from scraper import fetch_all_product_links, scrape_product

        links = fetch_all_product_links()

        sample_products = []
        for url in links[:5]:
            product = scrape_product(url)
            if product:
                sample_products.append(product)

        return JSONResponse(
            content={
                "status": "ok",
                "total_links": len(links),
                "sample_count": len(sample_products),
                "sample_products": sample_products,
            }
        )

    except Exception as e:
        logger.exception("Debug products failed: %s", e)
        raise HTTPException(
            status_code=500,
            detail=f"Debug products failed: {str(e)}",
        )


@app.post("/send-random-product")
async def send_random_product():
    """
    Manually trigger a product post to Telegram.
    Useful for testing before the scheduler runs.
    """
    if not BOT_TOKEN:
        raise HTTPException(
            status_code=503,
            detail="BOT_TOKEN is not configured. Set it in environment variables.",
        )

    logger.info("Manual post triggered via /send-random-product")

    success = post_product_job()

    if success:
        return JSONResponse(
            content={
                "status": "success",
                "message": "Product posted to Telegram.",
            }
        )

    raise HTTPException(
        status_code=500,
        detail="Failed to post product. Check logs for details.",
    )