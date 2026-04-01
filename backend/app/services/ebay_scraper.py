"""
eBay completed listings scraper for card research.
Uses httpx + selectolax to scrape public eBay search results.
"""
import asyncio
import hashlib
import random
import re
from datetime import datetime, timedelta
from typing import Optional
from urllib.parse import quote_plus

import httpx
from selectolax.parser import HTMLParser

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "en-US,en;q=0.9",
    "Accept-Encoding": "gzip, deflate, br",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
}

# In-memory cache: {query_hash: {"data": [...], "expires": datetime}}
_cache: dict[str, dict] = {}
CACHE_TTL_HOURS = 4


def _cache_key(req: dict) -> str:
    today = datetime.now().strftime("%Y-%m-%d")
    s = f"{req}_{today}"
    return hashlib.md5(s.encode()).hexdigest()


def _build_query(player_name: str, year: Optional[int], variation: Optional[str]) -> str:
    parts = ["PSA 10"]
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


def _is_captcha_page(html: str) -> bool:
    lower = html.lower()
    return "security measure" in lower or "captcha" in lower or "robot" in lower


async def scrape_completed_listings(
    player_name: str,
    year: Optional[int] = None,
    variation: Optional[str] = None,
    min_price: Optional[float] = None,
    max_price: Optional[float] = None,
    max_results: int = 25,
) -> list[dict]:
    req_key = _cache_key({"p": player_name, "y": year, "v": variation, "min": min_price, "max": max_price})

    # Check cache
    if req_key in _cache and _cache[req_key]["expires"] > datetime.now():
        return _cache[req_key]["data"]

    query = _build_query(player_name, year, variation)
    encoded = quote_plus(query)

    price_filter = ""
    if min_price:
        price_filter += f"&_udlo={min_price}"
    if max_price:
        price_filter += f"&_udhi={max_price}"

    url = (
        f"https://www.ebay.com/sch/i.html"
        f"?_nkw={encoded}"
        f"&LH_Complete=1&LH_Sold=1"
        f"&_sop=13"  # sort by most recently ended
        f"&_sacat=212"  # sports trading cards category
        f"{price_filter}"
    )

    results = []
    try:
        async with httpx.AsyncClient(headers=HEADERS, follow_redirects=True, timeout=15) as client:
            # Warm up with a root request to get cookies
            try:
                await client.get("https://www.ebay.com", timeout=8)
            except Exception:
                pass

            await asyncio.sleep(random.uniform(1.5, 3.0))

            resp = await client.get(url)
            if resp.status_code == 403 or _is_captcha_page(resp.text):
                raise RuntimeError("ebay_rate_limited")

            tree = HTMLParser(resp.text)

            for item in tree.css("li.s-item"):
                title_el = item.css_first(".s-item__title")
                price_el = item.css_first(".s-item__price")
                date_el = item.css_first(".s-item__ended-date")
                img_el = item.css_first(".s-item__image-img")
                link_el = item.css_first(".s-item__link")

                if not title_el or not price_el:
                    continue

                title = title_el.text(strip=True)
                if "shop on ebay" in title.lower():
                    continue

                price_text = price_el.text(strip=True)
                # Skip range prices for now
                if "to" in price_text.lower():
                    continue
                price = _parse_price(price_text)
                if price is None:
                    continue

                # Filter to PSA 10 only
                title_upper = title.upper()
                if "PSA" not in title_upper and "PSA10" not in title_upper:
                    continue
                if "PSA 10" not in title_upper and "PSA10" not in title_upper:
                    continue

                results.append({
                    "title": title,
                    "price": price,
                    "sale_date": date_el.text(strip=True) if date_el else None,
                    "image_url": img_el.attributes.get("src") if img_el else None,
                    "listing_url": link_el.attributes.get("href") if link_el else None,
                    "grade": "PSA 10",
                })

                if len(results) >= max_results:
                    break

    except RuntimeError:
        raise
    except Exception as e:
        # Return empty on network errors rather than crash
        pass

    # Cache results
    _cache[req_key] = {
        "data": results,
        "expires": datetime.now() + timedelta(hours=CACHE_TTL_HOURS),
    }
    return results
