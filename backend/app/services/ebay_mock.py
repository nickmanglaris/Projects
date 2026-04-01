"""
Mock eBay data service.
Used when EBAY_CLIENT_ID is not configured.
Generates deterministic, realistic-looking transaction data.
"""
import random
from datetime import date, timedelta
from typing import Any

SEED = 42

CARD_TEMPLATES = [
    ("Wander Franco", 2021, "Bowman Chrome", "PSA 10"),
    ("Gunnar Henderson", 2022, "Bowman Chrome Prospect", "PSA 10"),
    ("Jackson Holliday", 2023, "Bowman Chrome Prospect", "PSA 10"),
    ("Corbin Carroll", 2022, "Topps Chrome", "PSA 10"),
    ("Julio Rodriguez", 2021, "Bowman Chrome", "PSA 10"),
    ("Bobby Witt Jr.", 2021, "Bowman Chrome Autograph", "PSA 10"),
    ("Francisco Alvarez", 2022, "Bowman Chrome Prospect", "PSA 10"),
    ("Anthony Volpe", 2022, "Bowman Chrome", "PSA 10"),
    ("Jordan Walker", 2022, "Bowman Chrome Prospect", "PSA 10"),
    ("Evan Carter", 2022, "Bowman Chrome Autograph", "PSA 10"),
    ("Druw Jones", 2022, "Bowman Chrome Draft", "PSA 10"),
    ("Jasson Dominguez", 2021, "Bowman Chrome Prospect", "PSA 10"),
    ("Elijah Green", 2022, "Bowman Chrome Draft", "PSA 10"),
    ("Chase DeLauter", 2022, "Bowman Chrome Draft", "PSA 10"),
    ("Dylan Crews", 2023, "Bowman Chrome Draft", "PSA 10"),
]

PURCHASE_PRICES = [45, 55, 65, 75, 85, 95, 110, 125, 140, 160, 180, 200, 225, 250, 300]
SALE_MULTIPLIERS = [1.15, 1.20, 1.25, 1.30, 1.35, 1.40, 1.50, 1.60, 0.95, 1.10]


def _make_transactions(days: int = 365) -> list[dict[str, Any]]:
    rng = random.Random(SEED)
    today = date.today()
    start = today - timedelta(days=days)

    transactions = []
    tx_id = 1

    for i, (player, year, variation, grade) in enumerate(CARD_TEMPLATES):
        # Purchase
        purchase_offset = rng.randint(0, days - 30)
        purchase_date = start + timedelta(days=purchase_offset)
        purchase_price = rng.choice(PURCHASE_PRICES)
        ebay_fees_pct = rng.uniform(0.12, 0.135)
        shipping = rng.choice([4.99, 5.99, 6.99, 8.99])
        card_name = f"{year} {variation} {player} {grade}"

        transactions.append({
            "id": tx_id,
            "ebay_item_id": f"MOCK{300000000 + i * 1000 + 1}",
            "transaction_type": "purchase",
            "card_name": card_name,
            "player_name": player,
            "year": year,
            "variation": variation,
            "grade": grade,
            "amount": float(purchase_price),
            "ebay_fees": 0.0,
            "shipping_cost": shipping,
            "net_amount": -(purchase_price + shipping),
            "transaction_date": purchase_date.isoformat(),
            "source": "ebay",
            "reconciled": purchase_offset < days - 60,
            "notes": None,
            "created_at": purchase_date.isoformat(),
        })
        tx_id += 1

        # Sale for most cards (simulate ~80% sell-through)
        if rng.random() < 0.80:
            sale_offset = purchase_offset + rng.randint(20, 90)
            if sale_offset <= days:
                sale_date = start + timedelta(days=sale_offset)
                multiplier = rng.choice(SALE_MULTIPLIERS)
                sale_price = round(purchase_price * multiplier, 2)
                fees = round(sale_price * rng.uniform(0.12, 0.135), 2)
                sale_net = round(sale_price - fees - shipping, 2)

                transactions.append({
                    "id": tx_id,
                    "ebay_item_id": f"MOCK{300000000 + i * 1000 + 2}",
                    "transaction_type": "sale",
                    "card_name": card_name,
                    "player_name": player,
                    "year": year,
                    "variation": variation,
                    "grade": grade,
                    "amount": float(sale_price),
                    "ebay_fees": float(fees),
                    "shipping_cost": shipping,
                    "net_amount": float(sale_net),
                    "transaction_date": sale_date.isoformat(),
                    "source": "ebay",
                    "reconciled": sale_offset < days - 60,
                    "notes": None,
                    "created_at": sale_date.isoformat(),
                })
                tx_id += 1

    transactions.sort(key=lambda x: x["transaction_date"])
    return transactions


def get_mock_transactions(days: int = 365, tx_type: str | None = None) -> list[dict]:
    txns = _make_transactions(days)
    if tx_type:
        txns = [t for t in txns if t["transaction_type"] == tx_type]
    return txns


def get_mock_summary(period: str = "12m") -> dict:
    days = {"30d": 30, "90d": 90, "6m": 180, "12m": 365, "all": 730}.get(period, 365)
    txns = _make_transactions(days)
    sales = [t for t in txns if t["transaction_type"] == "sale"]
    purchases = [t for t in txns if t["transaction_type"] == "purchase"]

    revenue = sum(t["amount"] for t in sales)
    costs = sum(t["amount"] + t["shipping_cost"] for t in purchases)
    profit = sum(t["net_amount"] for t in sales) - 0  # net_amount already deducts fees
    # Recalculate profit correctly
    total_sale_net = sum(t["net_amount"] for t in sales)
    total_purchase_cost = sum(t["amount"] + t["shipping_cost"] for t in purchases)
    true_profit = total_sale_net - total_purchase_cost + sum(t["amount"] for t in purchases)
    # Simpler: profit = revenue - fees - purchases
    revenue_total = round(revenue, 2)
    cost_total = round(total_purchase_cost, 2)
    profit_total = round(revenue_total - sum(t["ebay_fees"] + t["shipping_cost"] for t in sales) - cost_total, 2)
    roi_pct = round((profit_total / cost_total * 100) if cost_total > 0 else 0, 1)

    return {
        "revenue_total": revenue_total,
        "cost_total": cost_total,
        "profit_total": profit_total,
        "roi_pct": roi_pct,
        "period": period,
        "is_mock": True,
        "transaction_count": len(txns),
        "avg_profit_per_card": round(profit_total / max(len(sales), 1), 2),
    }


def get_mock_trajectory(period: str = "12m") -> list[dict]:
    days = {"30d": 30, "90d": 90, "6m": 180, "12m": 365, "all": 730}.get(period, 365)
    txns = _make_transactions(days)

    from collections import defaultdict
    monthly: dict[str, dict] = defaultdict(lambda: {"revenue": 0.0, "cost": 0.0, "fees": 0.0, "shipping_sell": 0.0})

    for t in txns:
        month = t["transaction_date"][:7]  # YYYY-MM
        if t["transaction_type"] == "sale":
            monthly[month]["revenue"] += t["amount"]
            monthly[month]["fees"] += t["ebay_fees"]
            monthly[month]["shipping_sell"] += t["shipping_cost"]
        else:
            monthly[month]["cost"] += t["amount"] + t["shipping_cost"]

    result = []
    cumulative = 0.0
    for month in sorted(monthly.keys()):
        d = monthly[month]
        profit = d["revenue"] - d["fees"] - d["shipping_sell"] - d["cost"]
        cumulative += profit
        result.append({
            "date": month,
            "revenue": round(d["revenue"], 2),
            "cost": round(d["cost"], 2),
            "profit": round(profit, 2),
            "cumulative_profit": round(cumulative, 2),
        })

    return result
