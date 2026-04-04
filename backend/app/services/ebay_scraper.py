"""
eBay raw card listings scraper.
Searches for ungraded cards and returns listings with images for PSA 10 analysis.
"""
import asyncio
import hashlib
import logging
import random
import re
from datetime import datetime, timedelta
from typing import Optional
from urllib.parse import quote_plus

import httpx
from selectolax.parser import HTMLParser

logger = logging.getLogger(__name__)

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "en-US,en;q=0.9",
    "Accept-Encoding": "gzip, deflate, br",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
    "Referer": "https://www.ebay.com/",
}

# Terms that indicate a card is already graded — skip these
GRADED_TERMS = ["psa", "bgs", "sgc", "cgc", "hga", "ace", "graded", "gem mt", "mint 10"]

_cache: dict[str, dict] = {}
CACHE_TTL_HOURS = 2


def _cache_key(req: dict) -> str:
    today = datetime.now().strftime("%Y-%m-%d-%H")
    return hashlib.md5(f"{req}_{today}".encode()).hexdigest()


def _build_query(player_name: str, year: Optional[int], variation: Optional[str]) -> str:
    parts = []
    if year:
        parts.append(str(year))
    parts.append(player_name)
    if variation:
        parts.append(variation)
    return " ".join(parts)


def _parse_price(text: str) -> Optional[float]:
    if not text:
        return None
    text = text.replace(",", "").strip()
    m = re.search(r"\$?([\d.]+)", text)
    if m:
        try:
            return float(m.group(1))
        except ValueError:
            return None
    return None


def _is_graded(title: str) -> bool:
    t = title.lower()
    return any(term in t for term in GRADED_TERMS)


def _is_captcha_page(html: str) -> bool:
    lower = html.lower()
    return "security measure" in lower or "captcha" in lower or "robot" in lower


async def scrape_raw_listings(
    player_name: str,
    year: Optional[int] = None,
    variation: Optional[str] = None,
    min_price: Optional[float] = None,
    max_price: Optional[float] = None,
    max_results: int = 20,
) -> list[dict]:
    req_key = _cache_key({"p": player_name, "y": year, "v": variation, "min": min_price, "max": max_price})

    if req_key in _cache and _cache[req_key]["expires"] > datetime.now():
        cached = _cache[req_key]["data"]
        # Don't serve empty cache — retry the scrape
        if cached:
            logger.info(f"Returning {len(cached)} cached results")
            return cached
        logger.info("Cache had empty results — retrying scrape")

    query = _build_query(player_name, year, variation)
    encoded = quote_plus(query)

    price_filter = ""
    if min_price:
        price_filter += f"&_udlo={min_price}"
    if max_price:
        price_filter += f"&_udhi={max_price}"

    # Search active listings (not completed) for raw cards to buy
    url = (
        f"https://www.ebay.com/sch/i.html"
        f"?_nkw={encoded}"
        f"&_sacat=212"       # sports trading cards
        f"&LH_BIN=1"         # Buy It Now listings (have clearer photos)
        f"&_sop=15"          # sort by lowest price first
        f"&_ipg=48"          # 48 results per page
        f"{price_filter}"
    )

    logger.info(f"Scraping URL: {url}")
    results = []
    try:
        async with httpx.AsyncClient(headers=HEADERS, follow_redirects=True, timeout=20) as client:
            try:
                await client.get("https://www.ebay.com", timeout=8)
            except Exception:
                pass

            await asyncio.sleep(random.uniform(1.5, 3.0))

            resp = await client.get(url)
            logger.info(f"Response size: {len(resp.text)} chars")
            logger.info(f"eBay scrape status: {resp.status_code} | query: '{query}'")

            if resp.status_code == 403 or _is_captcha_page(resp.text):
                raise RuntimeError("ebay_rate_limited")

            tree = HTMLParser(resp.text)

            # Try multiple selectors — eBay periodically changes structure
            items = (
                tree.css("li.s-item")
                or tree.css("div.s-item")
                or tree.css("[class*='s-item']")
            )
            logger.info(f"eBay raw items found on page: {len(items)}")

            # Always probe the HTML structure to understand what eBay is serving
            for probe in ["s-item", "srp-results", "b-list__item", "itmHldr", "lvresult", "data-view", "s-item__title"]:
                count = resp.text.count(probe)
                logger.info(f"  HTML pattern '{probe}': {count} occurrences")

            # Log first matched item's raw HTML for selector debugging
            if items:
                logger.info(f"First item HTML: {items[0].html[:500]}")

            # Also try finding any li elements as a broader probe
            all_li = tree.css("li")
            logger.info(f"Total <li> elements on page: {len(all_li)}")
            if all_li:
                logger.info(f"First <li> sample: {all_li[0].html[:300]}")

            for item in items:
                title_el = item.css_first(".s-item__title") or item.css_first("[class*='s-item__title']")
                price_el = item.css_first(".s-item__price") or item.css_first("[class*='s-item__price']")
                img_el = (
                    item.css_first(".s-item__image-img")
                    or item.css_first("img.s-item__image-img")
                    or item.css_first(".s-item__image img")
                )
                link_el = item.css_first(".s-item__link") or item.css_first("a[href*='itm/']")

                if not title_el or not price_el:
                    continue

                title = title_el.text(strip=True)
                if not title or "shop on ebay" in title.lower():
                    continue

                # Skip already-graded cards
                if _is_graded(title):
                    continue

                price_text = price_el.text(strip=True)
                if " to " in price_text.lower():
                    continue
                price = _parse_price(price_text)
                if price is None:
                    continue

                # Get highest quality image URL available
                image_url = None
                if img_el:
                    # Try to get the full size image by modifying the thumbnail URL
                    src = img_el.attributes.get("src") or img_el.attributes.get("data-src") or ""
                    # eBay thumbnails end in s-l140.jpg or s-l225.jpg — upgrade to s-l500
                    image_url = re.sub(r"s-l\d+\.jpg", "s-l500.jpg", src) if src else None

                listing_url = link_el.attributes.get("href") if link_el else None
                # Clean tracking params from URL
                if listing_url and "?" in listing_url:
                    listing_url = listing_url.split("?")[0]

                results.append({
                    "title": title,
                    "price": price,
                    "image_url": image_url,
                    "listing_url": listing_url,
                    "grade": "raw",
                    "sale_date": None,
                })

                if len(results) >= max_results:
                    break

        logger.info(f"Raw listings after graded filter: {len(results)}")

    except RuntimeError:
        raise
    except Exception as e:
        logger.error(f"eBay scraper error: {type(e).__name__}: {e}")

    _cache[req_key] = {
        "data": results,
        "expires": datetime.now() + timedelta(hours=CACHE_TTL_HOURS),
    }
    return results
