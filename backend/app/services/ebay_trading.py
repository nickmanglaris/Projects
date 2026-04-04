"""
eBay Sell Finances API + Trading API integration.
Fetches sales and purchase transactions for the P&L dashboard.
"""
import logging
import xml.etree.ElementTree as ET
from datetime import date, datetime, timedelta
from typing import Optional

import httpx

logger = logging.getLogger(__name__)

FINANCES_BASE = "https://apiz.ebay.com/sell/finances/v1"


def _parse_float(val: Optional[str]) -> float:
    try:
        return abs(float(val or 0))
    except (ValueError, TypeError):
        return 0.0


async def fetch_ebay_sales(user_token: str, days: int = 90) -> list[dict]:
    """
    Fetch SALE transactions from eBay Sell Finances API.
    Returns a list of dicts ready to insert as Transaction records.
    """
    from_date = (datetime.utcnow() - timedelta(days=days)).strftime("%Y-%m-%dT%H:%M:%S.000Z")

    headers = {
        "Authorization": f"Bearer {user_token}",
        "Content-Type": "application/json",
    }

    results = []
    offset = 0
    limit = 200

    async with httpx.AsyncClient(timeout=30) as client:
        while True:
            params = {
                "transaction_type": "SALE",
                "transaction_date_range.from": from_date,
                "limit": limit,
                "offset": offset,
            }

            resp = await client.get(
                f"{FINANCES_BASE}/transaction",
                headers=headers,
                params=params,
            )

            if resp.status_code == 401:
                logger.error("eBay User Token expired or invalid — re-authorize in .env")
                break

            if not resp.is_success:
                logger.error(f"Finances API {resp.status_code}: {resp.text[:400]}")
                break

            data = resp.json()
            transactions = data.get("transactions", [])
            logger.info(f"Finances API page offset={offset}: {len(transactions)} transactions")

            for tx in transactions:
                tx_type = tx.get("transactionType", "")
                if tx_type != "SALE":
                    continue

                amount_info = tx.get("amount", {})
                fee_info = tx.get("totalFeeAmount", {})
                order_line_items = tx.get("orderLineItems") or []

                # Get item title from first line item
                title = "eBay Sale"
                if order_line_items:
                    title = order_line_items[0].get("title") or "eBay Sale"

                amount = _parse_float(amount_info.get("value"))
                fees = _parse_float(fee_info.get("value") if fee_info else None)
                order_id = tx.get("orderId", "")
                tx_date_raw = tx.get("transactionDate", "")
                try:
                    tx_date = date.fromisoformat(tx_date_raw[:10]) if tx_date_raw else date.today()
                except ValueError:
                    tx_date = date.today()

                results.append({
                    "ebay_item_id": order_id,
                    "transaction_type": "sale",
                    "card_name": title,
                    "amount": round(amount, 2),
                    "ebay_fees": round(fees, 2),
                    "shipping_cost": 0.0,
                    "transaction_date": tx_date,
                    "source": "ebay",
                })

            total = data.get("total", 0)
            offset += len(transactions)
            if offset >= total or not transactions:
                break

    logger.info(f"Fetched {len(results)} sales from eBay Finances API")
    return results


_TRADING_API = "https://api.ebay.com/ws/api.dll"
_NS = "urn:ebay:apis:eBLBaseComponents"


async def fetch_ebay_purchases(user_token: str, days: int = 90) -> list[dict]:
    """
    Fetch completed buyer orders from eBay Trading API (GetOrders).
    Returns a list of dicts ready to insert as Transaction records.
    """
    from_dt = (datetime.utcnow() - timedelta(days=days)).strftime("%Y-%m-%dT%H:%M:%S.000Z")
    to_dt = datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%S.000Z")

    headers = {
        "X-EBAY-API-SITEID": "0",
        "X-EBAY-API-COMPATIBILITY-LEVEL": "967",
        "X-EBAY-API-CALL-NAME": "GetOrders",
        "X-EBAY-API-IAF-TOKEN": user_token,
        "Content-Type": "text/xml",
    }

    results = []
    page = 1

    async with httpx.AsyncClient(timeout=30) as client:
        while True:
            body = f"""<?xml version="1.0" encoding="utf-8"?>
<GetOrdersRequest xmlns="{_NS}">
  <OrderRole>Buyer</OrderRole>
  <OrderStatus>Completed</OrderStatus>
  <CreateTimeFrom>{from_dt}</CreateTimeFrom>
  <CreateTimeTo>{to_dt}</CreateTimeTo>
  <Pagination>
    <EntriesPerPage>100</EntriesPerPage>
    <PageNumber>{page}</PageNumber>
  </Pagination>
</GetOrdersRequest>"""

            resp = await client.post(_TRADING_API, headers=headers, content=body)
            logger.info(f"Trading API status: {resp.status_code} (page {page})")

            if not resp.is_success:
                logger.error(f"Trading API error: {resp.text[:400]}")
                break

            root = ET.fromstring(resp.text)
            ns = {"e": _NS}

            ack = root.findtext("e:Ack", namespaces=ns) or ""
            if ack not in ("Success", "Warning"):
                msgs = [el.text for el in root.findall(".//e:ShortMessage", ns)]
                logger.error(f"Trading API failure: {msgs}")
                break

            orders = root.findall(".//e:Order", ns)
            logger.info(f"Trading API page {page}: {len(orders)} orders")

            for order in orders:
                order_id = order.findtext("e:OrderID", namespaces=ns) or ""
                amount_paid = order.findtext("e:AmountPaid", namespaces=ns) or "0"
                created_time = order.findtext("e:CreatedTime", namespaces=ns) or ""

                # Grab first item title
                title_el = order.find(".//e:Title", ns)
                title = title_el.text if title_el is not None else "eBay Purchase"

                try:
                    tx_date = date.fromisoformat(created_time[:10]) if created_time else date.today()
                except ValueError:
                    tx_date = date.today()

                results.append({
                    "ebay_item_id": f"buy_{order_id}",  # prefix avoids collision with sales IDs
                    "transaction_type": "purchase",
                    "card_name": title,
                    "amount": round(_parse_float(amount_paid), 2),
                    "ebay_fees": 0.0,
                    "shipping_cost": 0.0,
                    "transaction_date": tx_date,
                    "source": "ebay",
                })

            has_more = root.findtext("e:HasMoreOrders", namespaces=ns)
            if has_more != "true" or not orders:
                break
            page += 1

    logger.info(f"Fetched {len(results)} purchases from eBay Trading API")
    return results
