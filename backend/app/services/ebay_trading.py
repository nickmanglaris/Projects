"""
eBay Sell Finances API integration.
Fetches sales transactions (amount, fees, item title) for P&L dashboard.
"""
import logging
from datetime import datetime, timedelta
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
                tx_date = tx_date_raw[:10] if tx_date_raw else datetime.utcnow().strftime("%Y-%m-%d")

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
