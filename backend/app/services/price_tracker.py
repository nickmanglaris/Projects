"""
Daily price tracker service.
Fetches raw card prices from eBay and PSA 10/9/8 prices from 130point.com.
"""
import logging
import statistics
from datetime import date, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.card import Card
from app.models.price_history import PriceHistory
from app.services.ebay_scraper import fetch_psa_completed_prices, scrape_raw_listings
from app.services.price_tracker_130 import fetch_130point_prices

logger = logging.getLogger(__name__)


async def snapshot_all_watchlist(db: AsyncSession) -> dict:
    """Run a price snapshot for all cards on the watchlist."""
    result = await db.execute(
        select(Card).where(Card.is_watchlist == True)
    )
    cards = result.scalars().all()

    updated = 0
    failed = 0
    for card in cards:
        try:
            await snapshot_card(db, card)
            updated += 1
        except Exception as e:
            logger.warning(f"Price snapshot failed for card {card.id} ({card.card_name}): {e}")
            failed += 1

    return {"updated": updated, "failed": failed, "total": len(cards)}


async def snapshot_card(db: AsyncSession, card: Card) -> PriceHistory | None:
    """Fetch current prices for a single card and store a snapshot."""
    today = date.today()

    # Check if we already have a snapshot today
    existing = await db.execute(
        select(PriceHistory).where(
            PriceHistory.card_id == card.id,
            PriceHistory.snapshot_date == today,
        )
    )
    if existing.scalar_one_or_none():
        return None  # Already snapshotted today

    # Run eBay and 130point fetches independently
    results = await scrape_raw_listings(
        player_name=card.player_name or card.card_name,
        year=card.year,
        variation=card.variation,
        max_results=20,
    )

    # Fetch PSA prices from eBay completed sales, fall back to 130point, aggregate if both
    name = card.player_name or card.card_name
    ebay_psa = {}
    for grade in [10, 9, 8]:
        ebay_psa[f"psa{grade}"] = await fetch_psa_completed_prices(
            player_name=name, grade=grade, year=card.year, card_set=card.variation
        )

    fallback_psa = {}
    if not any(ebay_psa.values()):
        logger.info(f"eBay PSA prices unavailable for {name}, trying 130point fallback")
        fallback_psa = await fetch_130point_prices(
            player_name=name, year=card.year, card_set=card.variation
        )

    graded_prices = {}
    for key in ("psa10", "psa9", "psa8"):
        ebay_val = ebay_psa.get(key)
        pt_val = fallback_psa.get(key)
        if ebay_val and pt_val:
            graded_prices[key] = round((ebay_val + pt_val) / 2, 2)
        else:
            graded_prices[key] = ebay_val or pt_val

    prices = [r["price"] for r in results if r.get("price")]
    avg = round(statistics.mean(prices), 2) if prices else None
    low = round(min(prices), 2) if prices else None
    high = round(max(prices), 2) if prices else None

    # Skip snapshot only if both sources returned nothing
    if avg is None and not any(graded_prices.values()):
        return None

    snapshot = PriceHistory(
        card_id=card.id,
        snapshot_date=today,
        avg_sale_price=avg,
        min_price=low,
        max_price=high,
        sample_count=len(prices),
        source="ebay+130point",
        psa10_price=graded_prices.get("psa10"),
        psa9_price=graded_prices.get("psa9"),
        psa8_price=graded_prices.get("psa8"),
    )
    db.add(snapshot)
    await db.commit()
    await db.refresh(snapshot)
    return snapshot


async def get_price_history(
    db: AsyncSession, card_id: int, weeks: int = 12
) -> list[PriceHistory]:
    from datetime import timedelta
    cutoff = date.today() - timedelta(weeks=weeks)
    result = await db.execute(
        select(PriceHistory)
        .where(PriceHistory.card_id == card_id, PriceHistory.snapshot_date >= cutoff)
        .order_by(PriceHistory.snapshot_date.asc())
    )
    return result.scalars().all()


def suggested_list_price(latest_avg: float | None) -> float | None:
    """Suggest a list price ~5% above recent avg to stay competitive."""
    if latest_avg is None:
        return None
    return round(latest_avg * 1.05, 2)
