"""
130point.com price scraper for PSA graded card prices.
Fetches actual sold prices (not just listings) for PSA 10, 9, and 8 grades.
Runs once daily per card — results cached for 23 hours.
"""
import asyncio
import hashlib
import logging
import random
import re
import statistics
from datetime import datetime, timedelta
from typing import Optional
from urllib.parse import quote_plus

from curl_cffi.requests import AsyncSession
from selectolax.parser import HTMLParser

logger = logging.getLogger(__name__)

BASE_URL = "https://130point.com/sales/"


_cache: dict[str, dict] = {}
CACHE_TTL_HOURS = 23


def _cache_key(query: str) -> str:
    today = datetime.now().strftime("%Y-%m-%d")
    return hashlib.md5(f"{query}_{today}".encode()).hexdigest()


def _build_query(
    player_name: str,
    grade: int,
    year: Optional[int] = None,
    card_set: Optional[str] = None,
    variation: Optional[str] = None,
) -> str:
    parts = []
    if year:
        parts.append(str(year))
    parts.append(player_name)
    if card_set:
        parts.append(card_set)
    if variation:
        parts.append(variation)
    parts.append(f"PSA {grade}")
    return " ".join(parts)


def _parse_price(text: str) -> Optional[float]:
    if not text:
        return None
    text = text.replace(",", "").strip()
    m = re.search(r"\$?([\d]+\.?[\d]*)", text)
    if m:
        try:
            return float(m.group(1))
        except ValueError:
            return None
    return None


async def _fetch_prices_for_grade(
    client: httpx.AsyncClient,
    query: str,
    top_n: int = 5,
) -> Optional[float]:
    """Fetch 130point page for a single query, return average of top N prices."""
    cache_key = _cache_key(query)
    if cache_key in _cache and _cache[cache_key]["expires"] > datetime.now():
        return _cache[cache_key]["data"]

    url = f"{BASE_URL}?q={quote_plus(query)}"
    logger.info(f"130point fetch: {url}")

    try:
        resp = await client.get(url)
        logger.info(f"130point status: {resp.status_code} | size: {len(resp.text)} chars")

        if not resp.is_success:
            logger.warning(f"130point non-200 for query '{query}'")
            return None

        tree = HTMLParser(resp.text)

        # Try multiple selector patterns — 130point may vary layout
        prices: list[float] = []

        # Pattern 1: table rows with price cells
        for row in tree.css("table tr"):
            cells = row.css("td")
            for cell in cells:
                text = cell.text(strip=True)
                if "$" in text or re.match(r"^\d+\.\d{2}$", text):
                    p = _parse_price(text)
                    if p and 1.0 < p < 50000:
                        prices.append(p)

        # Pattern 2: elements with price class
        if not prices:
            for el in tree.css(".price, .sale-price, [class*='price'], [class*='sale']"):
                text = el.text(strip=True)
                p = _parse_price(text)
                if p and 1.0 < p < 50000:
                    prices.append(p)

        # Pattern 3: any span/div containing a $ amount
        if not prices:
            for el in tree.css("span, div, td, li"):
                text = el.text(strip=True)
                if text.startswith("$") and len(text) < 12:
                    p = _parse_price(text)
                    if p and 1.0 < p < 50000:
                        prices.append(p)

        logger.info(f"130point prices found for '{query}': {prices[:top_n]}")

        if not prices:
            _cache[cache_key] = {"data": None, "expires": datetime.now() + timedelta(hours=1)}
            return None

        # Average the most recent top_n prices
        avg = round(statistics.mean(prices[:top_n]), 2)
        _cache[cache_key] = {"data": avg, "expires": datetime.now() + timedelta(hours=CACHE_TTL_HOURS)}
        return avg

    except Exception as e:
        logger.error(f"130point error for '{query}': {type(e).__name__}: {e}")
        return None


async def fetch_130point_prices(
    player_name: str,
    year: Optional[int] = None,
    card_set: Optional[str] = None,
    variation: Optional[str] = None,
) -> dict[str, Optional[float]]:
    """
    Fetch PSA 10, 9, and 8 prices from 130point for a given card.
    Returns {"psa10": float|None, "psa9": float|None, "psa8": float|None}
    """
    async with AsyncSession(impersonate="chrome124") as client:
        # Fetch grades sequentially with polite delays to avoid rate limiting
        results = {}
        for grade in [10, 9, 8]:
            query = _build_query(player_name, grade, year, card_set, variation)
            price = await _fetch_prices_for_grade(client, query)
            results[f"psa{grade}"] = price
            if grade != 8:
                await asyncio.sleep(random.uniform(2.0, 4.0))

    logger.info(
        f"130point results for {player_name}: "
        f"PSA10={results.get('psa10')} PSA9={results.get('psa9')} PSA8={results.get('psa8')}"
    )
    return results
