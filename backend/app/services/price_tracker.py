"""
Weekly price tracker service.
Fetches eBay completed listing prices for watched cards and stores snapshots.
"""
import logging
import statistics
from datetime import date, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.card import Card
from app.models.price_history import PriceHistory
from app.services.ebay_scraper import scrape_raw_listings

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

    results = await scrape_raw_listings(
        player_name=card.player_name or card.card_name,
        year=card.year,
        variation=card.variation,
        max_results=20,
    )

    if not results:
        return None

    prices = [r["price"] for r in results if r.get("price")]
    if not prices:
        return None

    avg = round(statistics.mean(prices), 2)
    low = round(min(prices), 2)
    high = round(max(prices), 2)

    snapshot = PriceHistory(
        card_id=card.id,
        snapshot_date=today,
        avg_sale_price=avg,
        min_price=low,
        max_price=high,
        sample_count=len(prices),
        source="ebay_completed",
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
