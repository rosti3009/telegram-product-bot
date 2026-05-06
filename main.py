import logging
import os
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse

from database import init_db
from scheduler import start_scheduler, stop_scheduler, post_product_job
from telegram_sender import test_connection
from config import BOT_TOKEN, CHANNEL_USERNAME

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
    # Startup
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

    # Shutdown
    stop_scheduler()
    logger.info("Bot stopped.")


# ── App ────────────────────────────────────────────────────────────────────────
app = FastAPI(
    title="Compass Grill Telegram Bot",
    description="Automatically posts products from compassgrill.co.il to Telegram.",
    version="1.0.0",
    lifespan=lifespan,
)


# ── Endpoints ──────────────────────────────────────────────────────────────────
@app.get("/health")
async def health_check():
    """Simple health check endpoint."""
    return JSONResponse(
        content={
            "status": "ok",
            "bot_token_set": bool(BOT_TOKEN),
            "channel": CHANNEL_USERNAME,
        }
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
            content={"status": "success", "message": "Product posted to Telegram."}
        )
    else:
        raise HTTPException(
            status_code=500,
            detail="Failed to post product. Check logs for details.",
        )
