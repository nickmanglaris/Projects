"""
eBay active listings via Trading API GetMyeBaySelling.
Returns current inventory with price, days listed, and listing URL.
"""
import logging
import xml.etree.ElementTree as ET
from datetime import datetime, timezone

import httpx

logger = logging.getLogger(__name__)

_TRADING_API = "https://api.ebay.com/ws/api.dll"
_NS = "urn:ebay:apis:eBLBaseComponents"


def _days_listed(start_time_str: str) -> int:
    """Calculate days since listing start time."""
    try:
        start = datetime.fromisoformat(start_time_str.replace("Z", "+00:00"))
        now = datetime.now(timezone.utc)
        return (now - start).days
    except Exception:
        return 0


async def fetch_active_listings(user_token: str) -> list[dict]:
    """
    Fetch all active eBay listings using GetMyeBaySelling.
    Returns list of dicts with listing details.
    """
    headers = {
        "X-EBAY-API-SITEID": "0",
        "X-EBAY-API-COMPATIBILITY-LEVEL": "967",
        "X-EBAY-API-CALL-NAME": "GetMyeBaySelling",
        "X-EBAY-API-IAF-TOKEN": user_token,
        "Content-Type": "text/xml",
    }

    results = []
    page = 1

    async with httpx.AsyncClient(timeout=30) as client:
        while True:
            body = f"""<?xml version="1.0" encoding="utf-8"?>
<GetMyeBaySellingRequest xmlns="{_NS}">
  <ActiveList>
    <Include>true</Include>
    <IncludeWatchCount>true</IncludeWatchCount>
    <Pagination>
      <EntriesPerPage>200</EntriesPerPage>
      <PageNumber>{page}</PageNumber>
    </Pagination>
    <Sort>TimeLeft</Sort>
  </ActiveList>
  <DetailLevel>ReturnAll</DetailLevel>
</GetMyeBaySellingRequest>"""

            resp = await client.post(_TRADING_API, headers=headers, content=body)
            logger.info(f"GetMyeBaySelling status: {resp.status_code} (page {page})")

            if not resp.is_success:
                logger.error(f"GetMyeBaySelling error: {resp.text[:400]}")
                break

            root = ET.fromstring(resp.text)
            ns = {"e": _NS}

            ack = root.findtext("e:Ack", namespaces=ns) or ""
            if ack not in ("Success", "Warning"):
                msgs = [el.text for el in root.findall(".//e:ShortMessage", ns)]
                logger.error(f"GetMyeBaySelling failure: {msgs}")
                break

            items = root.findall(".//e:ActiveList/e:ItemArray/e:Item", ns)
            logger.info(f"GetMyeBaySelling page {page}: {len(items)} listings")

            for item in items:
                item_id = item.findtext("e:ItemID", namespaces=ns) or ""
                title = item.findtext("e:Title", namespaces=ns) or "Unknown"
                start_time = item.findtext("e:ListingDetails/e:StartTime", namespaces=ns) or ""
                view_url = item.findtext("e:ListingDetails/e:ViewItemURL", namespaces=ns) or ""
                gallery_url = item.findtext("e:PictureDetails/e:GalleryURL", namespaces=ns) or ""
                quantity = int(item.findtext("e:QuantityAvailable", namespaces=ns) or "1")
                watch_count = int(item.findtext("e:WatchCount", namespaces=ns) or "0")

                price_el = item.find("e:SellingStatus/e:CurrentPrice", ns)
                price = float(price_el.text) if price_el is not None and price_el.text else 0.0

                days = _days_listed(start_time)

                results.append({
                    "item_id": item_id,
                    "title": title,
                    "price": round(price, 2),
                    "listed_date": start_time[:10] if start_time else None,
                    "days_listed": days,
                    "quantity": quantity,
                    "watch_count": watch_count,
                    "listing_url": view_url,
                    "image_url": gallery_url or None,
                })

            # Check for more pages
            total_pages = root.findtext(".//e:ActiveList/e:PaginationResult/e:TotalNumberOfPages", namespaces=ns)
            if not total_pages or page >= int(total_pages):
                break
            page += 1

    logger.info(f"Fetched {len(results)} active listings")
    return results
