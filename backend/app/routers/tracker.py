import asyncio

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel
from typing import Optional
from datetime import date

from app.database import get_db
from app.models.card import Card
from app.models.price_history import PriceHistory
from app.models.grading_submission import GradingSubmission
from app.schemas.prospects import (
    CardOut, PriceHistoryOut, WatchlistEntry,
    GradingSubmissionCreate, GradingSubmissionUpdate, GradingSubmissionOut,
)
from app.services.price_tracker import get_price_history, snapshot_all_watchlist, snapshot_card, suggested_list_price

router = APIRouter(prefix="/tracker", tags=["tracker"])


class WatchlistAdd(BaseModel):
    card_name: str
    player_name: Optional[str] = None
    year: Optional[int] = None
    variation: Optional[str] = None
    grade: Optional[str] = "PSA 10"


def _history_to_out(h: PriceHistory) -> PriceHistoryOut:
    return PriceHistoryOut(
        id=h.id,
        card_id=h.card_id,
        snapshot_date=h.snapshot_date.isoformat(),
        avg_sale_price=h.avg_sale_price,
        min_price=h.min_price,
        max_price=h.max_price,
        sample_count=h.sample_count,
        psa10_price=getattr(h, "psa10_price", None),
        psa9_price=getattr(h, "psa9_price", None),
        psa8_price=getattr(h, "psa8_price", None),
    )


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

        # Latest PSA prices from most recent snapshot that has them
        latest_psa10 = next((h.psa10_price for h in reversed(history) if getattr(h, "psa10_price", None)), None)
        latest_psa9 = next((h.psa9_price for h in reversed(history) if getattr(h, "psa9_price", None)), None)
        latest_psa8 = next((h.psa8_price for h in reversed(history) if getattr(h, "psa8_price", None)), None)

        entries.append(WatchlistEntry(
            card=CardOut.model_validate(card),
            latest_price=latest_price,
            price_change_pct=change_pct,
            suggested_list_price=suggested_list_price(latest_price),
            latest_psa10=latest_psa10,
            latest_psa9=latest_psa9,
            latest_psa8=latest_psa8,
            price_history=[_history_to_out(h) for h in history],
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
    return [_history_to_out(h) for h in history]


@router.post("/snapshot")
async def trigger_snapshot(db: AsyncSession = Depends(get_db)):
    stats = await snapshot_all_watchlist(db)
    return stats


# ── Grading Submissions ─────────────────────────────────────────────────────

@router.get("/grading", response_model=list[GradingSubmissionOut])
async def list_grading(db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(GradingSubmission).order_by(GradingSubmission.submitted_date.desc())
    )
    return result.scalars().all()


@router.post("/grading", response_model=GradingSubmissionOut, status_code=201)
async def create_grading(data: GradingSubmissionCreate, db: AsyncSession = Depends(get_db)):
    sub = GradingSubmission(**data.model_dump())
    db.add(sub)
    await db.commit()
    await db.refresh(sub)
    return sub


@router.patch("/grading/{sub_id}", response_model=GradingSubmissionOut)
async def update_grading(sub_id: int, data: GradingSubmissionUpdate, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(GradingSubmission).where(GradingSubmission.id == sub_id))
    sub = result.scalar_one_or_none()
    if not sub:
        raise HTTPException(status_code=404, detail="Submission not found")
    for field, val in data.model_dump(exclude_none=True).items():
        setattr(sub, field, val)
    await db.commit()
    await db.refresh(sub)
    return sub


@router.delete("/grading/{sub_id}", status_code=204)
async def delete_grading(sub_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(GradingSubmission).where(GradingSubmission.id == sub_id))
    sub = result.scalar_one_or_none()
    if not sub:
        raise HTTPException(status_code=404, detail="Submission not found")
    await db.delete(sub)
    await db.commit()


@router.post("/grading/{sub_id}/fetch-prices", response_model=GradingSubmissionOut)
async def fetch_grading_prices(sub_id: int, db: AsyncSession = Depends(get_db)):
    """Fetch PSA 10 and PSA 9 price estimates from 130point for a grading submission."""
    result = await db.execute(select(GradingSubmission).where(GradingSubmission.id == sub_id))
    sub = result.scalar_one_or_none()
    if not sub:
        raise HTTPException(status_code=404, detail="Submission not found")
    if not sub.player_name or not sub.year or not sub.card_set:
        raise HTTPException(status_code=400, detail="player_name, year, and card_set are required to fetch prices")

    from app.services.ebay_scraper import fetch_psa_completed_prices
    psa10 = await fetch_psa_completed_prices(sub.player_name, 10, sub.year, sub.card_set, sub.variation, max_results=5)
    await asyncio.sleep(0.5)
    psa9 = await fetch_psa_completed_prices(sub.player_name, 9, sub.year, sub.card_set, sub.variation, max_results=5)
    sub.psa10_estimate = psa10
    sub.psa9_estimate = psa9
    await db.commit()
    await db.refresh(sub)
    return sub
