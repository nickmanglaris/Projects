"""
MLB prospects data service.
Primary source: FanGraphs prospects board (public JSON endpoint).
Fallback: MLB Stats API for minor league players.
"""
import json
import logging
from datetime import datetime
from typing import Optional

import httpx
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.prospect import Prospect

logger = logging.getLogger(__name__)

FANGRAPHS_URL = (
    "https://www.fangraphs.com/api/prospects/prospects-pitcher-hitter-data"
    "?pos=&team=&world=1&draft=0"
)

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
    ),
    "Referer": "https://www.fangraphs.com/prospects/the-board",
    "Accept": "application/json",
}

RISING_THRESHOLD = 5  # spots moved up to be considered "rising"


async def fetch_and_store_prospects(db: AsyncSession) -> int:
    """Fetch prospects from FanGraphs and upsert into DB. Returns count updated."""
    try:
        data = await _fetch_fangraphs()
    except Exception as e:
        logger.warning(f"FanGraphs fetch failed: {e}. Skipping update.")
        return 0

    if not data:
        return 0

    count = 0
    for item in data[:100]:  # Top 100 only
        name = item.get("PlayerName") or item.get("Name") or ""
        if not name:
            continue

        rank = item.get("Rank") or item.get("rank")
        try:
            rank = int(rank) if rank else None
        except (ValueError, TypeError):
            rank = None

        mlb_id = str(item.get("PlayerID") or item.get("mlbamid") or "")

        # Look up existing
        result = await db.execute(
            select(Prospect).where(Prospect.name == name)
        )
        prospect = result.scalar_one_or_none()

        if prospect:
            old_rank = prospect.rank_current
            prospect.rank_previous = old_rank
            prospect.rank_current = rank
            if old_rank and rank:
                prospect.rank_change = old_rank - rank  # positive = moved up
                prospect.is_rising = prospect.rank_change >= RISING_THRESHOLD
            else:
                prospect.rank_change = 0
                prospect.is_rising = False
        else:
            prospect = Prospect(
                mlb_id=mlb_id or None,
                name=name,
                position=item.get("Pos") or item.get("position"),
                team=item.get("Team") or item.get("team"),
                rank_current=rank,
                rank_previous=None,
                rank_change=0,
                eta=str(item.get("ETA") or item.get("eta") or ""),
                scouting_grade=_format_grade(item),
                is_rising=False,
                source="fangraphs",
            )
            db.add(prospect)

        prospect.last_updated = datetime.now()
        count += 1

    await db.commit()
    return count


def _format_grade(item: dict) -> Optional[str]:
    fv = item.get("FV") or item.get("fv") or item.get("Grade")
    if fv:
        return f"{fv} FV"
    return None


async def _fetch_fangraphs() -> list[dict]:
    async with httpx.AsyncClient(headers=HEADERS, timeout=20) as client:
        resp = await client.get(FANGRAPHS_URL)
        resp.raise_for_status()
        data = resp.json()
        # FanGraphs returns {"pitcher": [...], "hitter": [...]} or flat list
        if isinstance(data, list):
            return data
        if isinstance(data, dict):
            combined = []
            for key in ("hitter", "pitcher", "prospects", "data"):
                if key in data and isinstance(data[key], list):
                    combined.extend(data[key])
            return combined
        return []


async def get_prospects(db: AsyncSession, rising_only: bool = False) -> list[Prospect]:
    query = select(Prospect).order_by(Prospect.rank_current.asc().nullslast())
    if rising_only:
        query = query.where(Prospect.is_rising == True)
    result = await db.execute(query)
    return result.scalars().all()
