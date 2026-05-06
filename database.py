import sqlite3
import logging
import os
from datetime import datetime, timedelta
from config import DB_PATH, DAYS_BEFORE_REPEAT

logger = logging.getLogger(__name__)


def _get_connection() -> sqlite3.Connection:
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db() -> None:
    """Create tables if they don't exist."""
    try:
        conn = _get_connection()
        conn.execute("""
            CREATE TABLE IF NOT EXISTS posted_products (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                product_url TEXT NOT NULL UNIQUE,
                product_name TEXT NOT NULL,
                posted_at TEXT NOT NULL
            )
        """)
        conn.commit()
        conn.close()
        logger.info("Database initialized at %s", DB_PATH)
    except Exception as e:
        logger.error("Failed to initialize database: %s", e)
        raise


def was_recently_posted(product_url: str) -> bool:
    """Return True if the product was posted within DAYS_BEFORE_REPEAT days."""
    try:
        cutoff = (datetime.utcnow() - timedelta(days=DAYS_BEFORE_REPEAT)).isoformat()
        conn = _get_connection()
        row = conn.execute(
            "SELECT id FROM posted_products WHERE product_url = ? AND posted_at >= ?",
            (product_url, cutoff),
        ).fetchone()
        conn.close()
        return row is not None
    except Exception as e:
        logger.error("Error checking posted status for %s: %s", product_url, e)
        return False


def mark_as_posted(product_url: str, product_name: str) -> None:
    """Insert or update the product as posted now."""
    try:
        now = datetime.utcnow().isoformat()
        conn = _get_connection()
        conn.execute(
            """
            INSERT INTO posted_products (product_url, product_name, posted_at)
            VALUES (?, ?, ?)
            ON CONFLICT(product_url) DO UPDATE SET posted_at = excluded.posted_at, product_name = excluded.product_name
            """,
            (product_url, product_name, now),
        )
        conn.commit()
        conn.close()
        logger.info("Marked as posted: %s", product_name)
    except Exception as e:
        logger.error("Error marking product as posted: %s", e)


def get_all_posted_urls() -> set[str]:
    """Return all product URLs that were ever posted."""
    try:
        conn = _get_connection()
        rows = conn.execute("SELECT product_url FROM posted_products").fetchall()
        conn.close()
        return {row["product_url"] for row in rows}
    except Exception as e:
        logger.error("Error fetching posted URLs: %s", e)
        return set()


def reset_cycle() -> None:
    """Clear all posted records to start a fresh cycle."""
    try:
        conn = _get_connection()
        conn.execute("DELETE FROM posted_products")
        conn.commit()
        conn.close()
        logger.info("Posted products cycle reset.")
    except Exception as e:
        logger.error("Error resetting cycle: %s", e)
