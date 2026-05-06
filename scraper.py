import json
import logging
import random
import re
from typing import Optional
from urllib.parse import urljoin, urlparse

import requests
from bs4 import BeautifulSoup

from config import CATEGORY_URLS, SITE_BASE_URL, REQUEST_HEADERS, REQUEST_TIMEOUT

logger = logging.getLogger(__name__)

PRICE_RE = re.compile(r"₪\s?[\d,]+(?:\.\d{1,2})?")


def _get(url: str) -> Optional[BeautifulSoup]:
    try:
        resp = requests.get(url, headers=REQUEST_HEADERS, timeout=REQUEST_TIMEOUT)
        resp.raise_for_status()
        return BeautifulSoup(resp.text, "html.parser")
    except requests.RequestException as e:
        logger.error("Failed to fetch %s: %s", url, e)
        return None


def _clean(text: str) -> str:
    return re.sub(r"\s+", " ", text or "").strip()


def _is_internal_url(url: str) -> bool:
    return urlparse(url).netloc.replace("www.", "") == urlparse(SITE_BASE_URL).netloc.replace("www.", "")


def _is_bad_link(href: str) -> bool:
    bad_parts = [
        "/cart", "/checkout", "/account", "/login", "/register", "/wishlist",
        "/contact", "/about", "/blog", "/sitemap", "/privacy", "/terms",
        "api.whatsapp", "facebook", "instagram", "tel:", "mailto:",
        "#", "javascript:"
    ]
    h = href.lower()
    return any(part in h for part in bad_parts)


def _normalize_url(href: str) -> str:
    href = href.split("#")[0].strip()
    return urljoin(SITE_BASE_URL, href)


def _extract_prices_from_text(text: str) -> list[str]:
    prices = PRICE_RE.findall(text or "")
    clean_prices = []
    for p in prices:
        p = _clean(p)
        if p not in clean_prices:
            clean_prices.append(p)
    return clean_prices


def _extract_json_ld_product(soup: BeautifulSoup) -> dict:
    result = {}

    for script in soup.select('script[type="application/ld+json"]'):
        try:
            raw = script.string or script.get_text()
            if not raw:
                continue

            data = json.loads(raw)

            candidates = data if isinstance(data, list) else [data]

            for item in candidates:
                if isinstance(item, dict) and "@graph" in item:
                    candidates.extend(item.get("@graph", []))

            for item in candidates:
                if not isinstance(item, dict):
                    continue

                item_type = item.get("@type", "")
                if isinstance(item_type, list):
                    is_product = "Product" in item_type
                else:
                    is_product = item_type == "Product"

                if not is_product:
                    continue

                result["product_name"] = _clean(item.get("name", ""))

                image = item.get("image", "")
                if isinstance(image, list):
                    image = image[0] if image else ""
                result["product_image"] = image

                result["description"] = _clean(item.get("description", ""))

                offers = item.get("offers", {})
                if isinstance(offers, list):
                    offers = offers[0] if offers else {}

                if isinstance(offers, dict):
                    price = offers.get("price") or offers.get("lowPrice") or ""
                    currency = offers.get("priceCurrency", "ILS")
                    if price:
                        result["price"] = f"₪{price}" if currency in ["ILS", "NIS"] else str(price)

                    availability = offers.get("availability", "")
                    if availability:
                        result["availability"] = "קיים במלאי" if "InStock" in availability else availability

                return result

        except Exception:
            continue

    return result


def _extract_product_links_from_category(category_url: str) -> list[str]:
    links: list[str] = []
    visited_pages: set[str] = set()
    page_url = category_url.rstrip("/") + "/"

    category_path = urlparse(page_url).path.strip("/")

    while page_url and page_url not in visited_pages:
        visited_pages.add(page_url)

        soup = _get(page_url)

        if not soup:
            break

        for a in soup.select("a[href]"):
            href = a.get("href", "")

            if not href:
                continue

            full_url = _normalize_url(href)
            full_url = full_url.split("?")[0].rstrip("/") + "/"

            if not _is_internal_url(full_url):
                continue

            if _is_bad_link(full_url):
                continue

            if full_url == page_url:
                continue

            parsed = urlparse(full_url)
            path = parsed.path.strip("/")

            if not path:
                continue

            # מוצר ב־iStore:
            # /category/product/
            if category_path and path.startswith(category_path + "/"):

                # חייב להיות לפחות עוד חלק אחד אחרי הקטגוריה
                remaining = path[len(category_path):].strip("/")

                if "/" not in remaining and remaining:

                    if full_url not in links:
                        links.append(full_url)

        # pagination
        next_link = None

        for a in soup.select("a[href]"):
            href = a.get("href", "")
            label = _clean(a.get_text(" ", strip=True))

            if (
                "page=" in href
                or "/page/" in href
                or label in {"הבא", ">", "»", "Next"}
            ):
                full_next = _normalize_url(href)
                full_next = full_next.split("?")[0].rstrip("/") + "/"

                if (
                    full_next not in visited_pages
                    and _is_internal_url(full_next)
                ):
                    next_link = full_next
                    break

        page_url = next_link

    logger.info("Found %d product links in %s", len(links), category_url)

    return links

def _extract_name(soup: BeautifulSoup) -> str:
    selectors = [
        "h1",
        ".product-title",
        ".product_name",
        ".product-name",
        "[itemprop='name']",
    ]

    for selector in selectors:
        tag = soup.select_one(selector)
        if tag:
            name = _clean(tag.get_text(" ", strip=True))
            if name and len(name) > 2:
                return name

    og_title = soup.select_one("meta[property='og:title']")
    if og_title and og_title.get("content"):
        return _clean(og_title["content"].split("|")[0])

    title = soup.select_one("title")
    if title:
        return _clean(title.get_text().split("|")[0])

    return ""


def _extract_image(soup: BeautifulSoup) -> str:
    meta_selectors = [
        "meta[property='og:image']",
        "meta[property='og:image:secure_url']",
        "meta[name='twitter:image']",
    ]

    for selector in meta_selectors:
        tag = soup.select_one(selector)
        if tag and tag.get("content"):
            return _normalize_url(tag["content"])

    img_selectors = [
        "img[itemprop='image']",
        ".product-info img",
        ".product-image img",
        ".product img",
        "main img",
        "img",
    ]

    for selector in img_selectors:
        img = soup.select_one(selector)
        if img:
            src = img.get("data-src") or img.get("data-original") or img.get("src")
            if src:
                return _normalize_url(src)

    return ""


def _extract_description(soup: BeautifulSoup) -> str:
    meta = soup.select_one("meta[name='description']")
    if meta and meta.get("content"):
        return _clean(meta["content"])[:500]

    selectors = [
        "#tab-description",
        ".description",
        ".product-description",
        ".product-info",
        "[itemprop='description']",
    ]

    for selector in selectors:
        tag = soup.select_one(selector)
        if tag:
            text = _clean(tag.get_text(" ", strip=True))
            if len(text) > 30:
                return text[:700]

    return ""


def _extract_specs(soup: BeautifulSoup) -> list[str]:
    specs: list[str] = []

    for li in soup.select("li"):
        text = _clean(li.get_text(" ", strip=True))

        if not text:
            continue

        if len(text) > 140:
            continue

        if text.startswith("✅"):
            specs.append(text.replace("✅", "").strip())
        elif any(word in text for word in ["מתאים", "טבעי", "איכותי", "נירוסטה", "ברזל", "עישון", "גריל", "טאבון"]):
            specs.append(text)

        if len(specs) >= 5:
            break

    unique = []
    for spec in specs:
        if spec not in unique:
            unique.append(spec)

    return unique[:5]


def _extract_prices(soup: BeautifulSoup) -> tuple[str, str]:
    text = _clean(soup.get_text(" ", strip=True))
    prices = _extract_prices_from_text(text)

    if not prices:
        return "", ""

    # In iStore product page often shows old price first and sale price second.
    # Example: ₪76.00 then ₪39.00
    if len(prices) >= 2:
        return prices[0], prices[1]

    return prices[0], ""


def _extract_availability(soup: BeautifulSoup) -> str:
    text = _clean(soup.get_text(" ", strip=True))

    if "אזל מהמלאי" in text:
        return "אזל מהמלאי"

    if "קיים במלאי" in text:
        return "קיים במלאי"

    if "זמינות:" in text:
        match = re.search(r"זמינות:\s*([^₪\n\r]{2,40})", text)
        if match:
            return _clean(match.group(1))

    return ""


def _extract_category(soup: BeautifulSoup) -> str:
    crumbs = []
    for a in soup.select("a"):
        text = _clean(a.get_text(" ", strip=True))
        href = a.get("href", "")
        if text and href and SITE_BASE_URL in _normalize_url(href):
            if text not in ["דף הבית", "ראשי", "החשבון שלי"]:
                crumbs.append(text)

    return crumbs[-2] if len(crumbs) >= 2 else ""


def _parse_product(url: str) -> Optional[dict]:
    soup = _get(url)
    if not soup:
        return None

    json_ld = _extract_json_ld_product(soup)

    product_name = json_ld.get("product_name") or _extract_name(soup)
    if not product_name:
        logger.warning("No product name found at %s", url)
        return None

    product_image = json_ld.get("product_image") or _extract_image(soup)
    description = json_ld.get("description") or _extract_description(soup)

    price, sale_price = _extract_prices(soup)

    if json_ld.get("price") and not price:
        price = json_ld["price"]

    availability = json_ld.get("availability") or _extract_availability(soup)

    return {
        "product_name": product_name,
        "product_url": url,
        "product_image": product_image,
        "price": price,
        "sale_price": sale_price,
        "description": description,
        "specs": _extract_specs(soup),
        "category": _extract_category(soup),
        "availability": availability,
    }


def fetch_all_product_links() -> list[str]:
    all_links: list[str] = []

    for category_url in CATEGORY_URLS:
        category_url = category_url.strip()
        if not category_url:
            continue

        links = _extract_product_links_from_category(category_url)
        all_links.extend(links)

    seen: set[str] = set()
    unique: list[str] = []

    for link in all_links:
        clean_link = link.rstrip("/") + "/"
        if clean_link not in seen:
            seen.add(clean_link)
            unique.append(clean_link)

    random.shuffle(unique)
    logger.info("Total unique product links fetched: %d", len(unique))
    return unique


def scrape_product(url: str) -> Optional[dict]:
    return _parse_product(url)