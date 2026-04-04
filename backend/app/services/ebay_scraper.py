"""
eBay raw card listings via the official eBay Finding API.
Searches for ungraded cards with PSA 10 potential.
"""
import hashlib
import logging
import re
from datetime import datetime, timedelta
from typing import Optional
from urllib.parse import urlencode

import httpx

from app.config import settings

logger = logging.getLogger(__name__)

FINDING_API = "https://svcs.ebay.com/services/search/FindingService/v1"

# Terms that indicate a card is already graded — filter post-API
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


def _is_graded(title: str) -> bool:
    t = title.lower()
    return any(term in t for term in GRADED_TERMS)


def _parse_price(val) -> Optional[float]:
    if val is None:
        return None
    try:
        return float(val)
    except (ValueError, TypeError):
        return None


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
        if cached:
            logger.info(f"Returning {len(cached)} cached results")
            return cached
        logger.info("Cache had empty results — retrying API call")

    app_id = settings.EBAY_CLIENT_ID
    if not app_id or app_id == "YOUR_CLIENT_ID_HERE":
        logger.error("EBAY_CLIENT_ID not set — cannot call Finding API")
        return []

    query = _build_query(player_name, year, variation)
    logger.info(f"eBay Finding API query: '{query}'")

    # Build query string manually so parentheses in filter keys are NOT percent-encoded
    # (eBay Finding API requires literal parentheses in parameter names)
    base_params = [
        ("OPERATION-NAME", "findItemsAdvanced"),
        ("SERVICE-VERSION", "1.0.0"),
        ("SECURITY-APPNAME", app_id),
        ("RESPONSE-DATA-FORMAT", "JSON"),
        ("keywords", query),
        ("categoryId", "212"),
        ("sortOrder", "PricePlusShippingLowest"),
        ("paginationInput.pageNumber", "1"),
        ("paginationInput.entriesPerPage", str(min(max_results, 100))),
        ("itemFilter(0).name", "ListingType"),
        ("itemFilter(0).value", "FixedPrice"),
    ]

    idx = 1
    if min_price is not None:
        base_params += [
            (f"itemFilter({idx}).name", "MinPrice"),
            (f"itemFilter({idx}).value", str(min_price)),
        ]
        idx += 1
    if max_price is not None:
        base_params += [
            (f"itemFilter({idx}).name", "MaxPrice"),
            (f"itemFilter({idx}).value", str(max_price)),
        ]

    # safe='' means don't encode anything extra; we keep parentheses literal
    qs = urlencode(base_params, safe="()")
    url = f"{FINDING_API}?{qs}"

    results = []
    try:
        async with httpx.AsyncClient(timeout=20) as client:
            resp = await client.get(url)
            logger.info(f"Finding API status: {resp.status_code}")

            if not resp.is_success:
                logger.error(f"Finding API error body: {resp.text[:500]}")
                resp.raise_for_status()

            data = resp.json()

        # Navigate JSON envelope
        root = data.get("findItemsAdvancedResponse", [{}])[0]
        ack = root.get("ack", ["Failure"])[0]
        logger.info(f"Finding API ack: {ack}")

        if ack not in ("Success", "Warning"):
            errors = root.get("errorMessage", [])
            logger.error(f"Finding API returned failure: {errors}")
            return []

        search_result = root.get("searchResult", [{}])[0]
        items = search_result.get("item", [])
        logger.info(f"Finding API returned {len(items)} raw items")

        for item in items:
            title = (item.get("title") or [""])[0]
            if not title:
                continue

            # Skip already-graded cards
            if _is_graded(title):
                continue

            view_url = (item.get("viewItemURL") or [""])[0]
            gallery_url = (item.get("galleryURL") or [""])[0]

            # Upgrade thumbnail to larger image
            image_url = re.sub(r"s-l\d+\.jpg", "s-l500.jpg", gallery_url) if gallery_url else None

            # Price
            selling = (item.get("sellingStatus") or [{}])[0]
            price_info = (selling.get("currentPrice") or [{}])[0]
            price = _parse_price(price_info.get("__value__"))

            if price is None:
                continue

            results.append({
                "title": title,
                "price": price,
                "image_url": image_url,
                "listing_url": view_url or None,
                "grade": "raw",
                "sale_date": None,
            })

            if len(results) >= max_results:
                break

    except Exception as e:
        logger.error(f"eBay Finding API error: {type(e).__name__}: {e}")

    logger.info(f"Raw listings returned: {len(results)}")
    _cache[req_key] = {
        "data": results,
        "expires": datetime.now() + timedelta(hours=CACHE_TTL_HOURS),
    }
    return results
