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


def _completed_items_url(app_id: str, query: str, max_results: int, end_time_from: Optional[str] = None) -> str:
    params = [
        ("OPERATION-NAME", "findCompletedItems"),
        ("SERVICE-VERSION", "1.0.0"),
        ("SECURITY-APPNAME", app_id),
        ("RESPONSE-DATA-FORMAT", "JSON"),
        ("keywords", query),
        ("categoryId", "212"),
        ("sortOrder", "EndTimeSoonest"),
        ("paginationInput.pageNumber", "1"),
        ("paginationInput.entriesPerPage", str(max_results)),
        ("itemFilter(0).name", "SoldItemsOnly"),
        ("itemFilter(0).value", "true"),
    ]
    if end_time_from:
        params += [
            ("itemFilter(1).name", "EndTimeFrom"),
            ("itemFilter(1).value", end_time_from),
        ]
    return f"{FINDING_API}?{urlencode(params, safe='()')}"


def _extract_prices(data: dict) -> list[float]:
    root = data.get("findCompletedItemsResponse", [{}])[0]
    ack = root.get("ack", ["Failure"])[0]
    if ack not in ("Success", "Warning"):
        return []
    items = root.get("searchResult", [{}])[0].get("item", [])
    prices = []
    for item in items:
        selling = (item.get("sellingStatus") or [{}])[0]
        price_info = (selling.get("currentPrice") or [{}])[0]
        p = _parse_price(price_info.get("__value__"))
        if p and p > 1.0:
            prices.append(p)
    return prices


async def fetch_psa_completed_prices(
    player_name: str,
    grade: int,
    year: Optional[int] = None,
    card_set: Optional[str] = None,
    variation: Optional[str] = None,
) -> Optional[float]:
    """
    Search eBay completed/sold listings for a specific PSA grade.
    Strategy:
      1. Last 7 days, up to 25 sales → average those
      2. If no recent sales → fetch last 1 sold as a reference point
    """
    parts = []
    if year:
        parts.append(str(year))
    parts.append(player_name)
    if card_set:
        parts.append(card_set)
    if variation:
        parts.append(variation)
    parts.append(f"PSA {grade}")
    query = " ".join(parts)

    req_key = _cache_key({"op": "completed", "q": query})
    if req_key in _cache and _cache[req_key]["expires"] > datetime.now():
        return _cache[req_key]["data"]

    app_id = settings.EBAY_CLIENT_ID
    if not app_id or app_id == "YOUR_CLIENT_ID_HERE":
        return None

    seven_days_ago = (datetime.utcnow() - timedelta(days=7)).strftime("%Y-%m-%dT%H:%M:%S.000Z")

    try:
        async with httpx.AsyncClient(timeout=20) as client:
            # Call 1: last 7 days, up to 25 results
            url = _completed_items_url(app_id, query, max_results=25, end_time_from=seven_days_ago)
            logger.info(f"completedItems (7d, PSA {grade}): '{query}'")
            resp = await client.get(url)
            logger.info(f"completedItems status: {resp.status_code}")
            if not resp.is_success:
                logger.error(f"completedItems error: {resp.text[:300]}")
                resp.raise_for_status()
            prices = _extract_prices(resp.json())
            logger.info(f"completedItems PSA {grade}: {len(prices)} sales in last 7 days")

            if not prices:
                # Call 2: no recent sales — fetch just the last sold as a reference
                url = _completed_items_url(app_id, query, max_results=1)
                logger.info(f"completedItems (last sold fallback, PSA {grade}): '{query}'")
                resp = await client.get(url)
                if resp.is_success:
                    prices = _extract_prices(resp.json())
                    if prices:
                        logger.info(f"completedItems PSA {grade} last sold: ${prices[0]}")

    except Exception as e:
        logger.error(f"eBay completedItems error: {type(e).__name__}: {e}")
        _cache[req_key] = {"data": None, "expires": datetime.now() + timedelta(hours=1)}
        return None

    if not prices:
        _cache[req_key] = {"data": None, "expires": datetime.now() + timedelta(hours=2)}
        return None

    avg = round(sum(prices) / len(prices), 2)
    logger.info(f"completedItems PSA {grade} avg: ${avg} (from {len(prices)} sale{'s' if len(prices) > 1 else ''})")
    _cache[req_key] = {"data": avg, "expires": datetime.now() + timedelta(hours=CACHE_TTL_HOURS)}
    return avg


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
