from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel
from typing import Optional
from datetime import date

from app.database import get_db
from app.models.card import Card
from app.models.price_history import PriceHistory
from app.schemas.prospects import CardOut, PriceHistoryOut, WatchlistEntry
from app.services.price_tracker import get_price_history, snapshot_all_watchlist, snapshot_card, suggested_list_price

router = APIRouter(prefix="/tracker", tags=["tracker"])


class WatchlistAdd(BaseModel):
    card_name: str
    player_name: Optional[str] = None
    year: Optional[int] = None
    variation: Optional[str] = None
    grade: Optional[str] = "PSA 10"


@router.get("/watchlist", response_model=list[WatchlistEntry])
async def get_watchlist(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Card).where(Card.is_watchlist == True))
    cards = result.scalars().all()

    entries = []
    for card in cards:
        history = await get_price_history(db, card.id, weeks=12)
        latest_price = history[-1].avg_sale_price if history else None
        prev_price = history[-2].avg_sale_price if len(history) >= 2 else None
        change_pct = None
        if latest_price and prev_price and prev_price > 0:
            change_pct = round((latest_price - prev_price) / prev_price * 100, 1)

        entries.append(WatchlistEntry(
            card=CardOut.model_validate(card),
            latest_price=latest_price,
            price_change_pct=change_pct,
            suggested_list_price=suggested_list_price(latest_price),
            price_history=[PriceHistoryOut(
                id=h.id,
                card_id=h.card_id,
                snapshot_date=h.snapshot_date.isoformat(),
                avg_sale_price=h.avg_sale_price,
                min_price=h.min_price,
                max_price=h.max_price,
                sample_count=h.sample_count,
            ) for h in history],
        ))
    return entries


@router.post("/watchlist", response_model=CardOut, status_code=201)
async def add_to_watchlist(data: WatchlistAdd, db: AsyncSession = Depends(get_db)):
    card = Card(
        card_name=data.card_name,
        player_name=data.player_name,
        year=data.year,
        variation=data.variation,
        grade=data.grade,
        is_watchlist=True,
        is_owned=False,
    )
    db.add(card)
    await db.commit()
    await db.refresh(card)
    # Kick off first price snapshot in background (best effort)
    try:
        await snapshot_card(db, card)
    except Exception:
        pass
    return CardOut.model_validate(card)


@router.delete("/watchlist/{card_id}", status_code=204)
async def remove_from_watchlist(card_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Card).where(Card.id == card_id))
    card = result.scalar_one_or_none()
    if not card:
        raise HTTPException(status_code=404, detail="Card not found")
    card.is_watchlist = False
    await db.commit()


@router.get("/history/{card_id}", response_model=list[PriceHistoryOut])
async def get_history(card_id: int, weeks: int = 12, db: AsyncSession = Depends(get_db)):
    history = await get_price_history(db, card_id, weeks)
    return [PriceHistoryOut(
        id=h.id,
        card_id=h.card_id,
        snapshot_date=h.snapshot_date.isoformat(),
        avg_sale_price=h.avg_sale_price,
        min_price=h.min_price,
        max_price=h.max_price,
        sample_count=h.sample_count,
    ) for h in history]


@router.post("/snapshot")
async def trigger_snapshot(db: AsyncSession = Depends(get_db)):
    stats = await snapshot_all_watchlist(db)
    return stats
