from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.prospect import Prospect
from app.schemas.prospects import ProspectOut, ProspectsResponse
from app.services.mlb_prospects import fetch_and_store_prospects, get_prospects

router = APIRouter(prefix="/prospects", tags=["prospects"])


@router.get("/top100", response_model=ProspectsResponse)
async def get_top100(db: AsyncSession = Depends(get_db)):
    prospects = await get_prospects(db)
    last_updated = max((p.last_updated for p in prospects if p.last_updated), default=None)
    return ProspectsResponse(
        prospects=[ProspectOut.model_validate(p) for p in prospects],
        last_updated=last_updated,
        total=len(prospects),
    )


@router.get("/rising", response_model=ProspectsResponse)
async def get_rising(threshold: int = Query(5), db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(Prospect)
        .where(Prospect.rank_change >= threshold)
        .order_by(Prospect.rank_change.desc())
    )
    prospects = result.scalars().all()
    last_updated = max((p.last_updated for p in prospects if p.last_updated), default=None)
    return ProspectsResponse(
        prospects=[ProspectOut.model_validate(p) for p in prospects],
        last_updated=last_updated,
        total=len(prospects),
    )


@router.post("/refresh")
async def refresh_prospects(db: AsyncSession = Depends(get_db)):
    count = await fetch_and_store_prospects(db)
    return {"updated": count, "message": f"Refreshed {count} prospects from FanGraphs."}


@router.get("/{prospect_id}", response_model=ProspectOut)
async def get_prospect(prospect_id: int, db: AsyncSession = Depends(get_db)):
    from fastapi import HTTPException
    result = await db.execute(select(Prospect).where(Prospect.id == prospect_id))
    prospect = result.scalar_one_or_none()
    if not prospect:
        raise HTTPException(status_code=404, detail="Prospect not found")
    return ProspectOut.model_validate(prospect)
