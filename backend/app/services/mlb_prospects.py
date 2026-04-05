"""
MLB Pipeline prospect data service.
Fetches top prospect rankings from mlb.com/milb/prospects.
Data is typically embedded as JSON in the page's __NEXT_DATA__ script tag.
"""
import json
import logging
import re
from datetime import datetime
from typing import Optional

from curl_cffi.requests import AsyncSession
from selectolax.parser import HTMLParser
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession as DBSession

from app.models.prospect import Prospect

logger = logging.getLogger(__name__)

PROSPECTS_URL = "https://www.mlb.com/milb/prospects"
RISING_THRESHOLD = 5


async def fetch_and_store_prospects(db: DBSession) -> int:
    """Fetch prospects from MLB Pipeline and upsert into DB. Returns count updated."""
    try:
        prospects_data = await _fetch_mlb_pipeline()
    except Exception as e:
        logger.warning(f"MLB Pipeline fetch failed: {e}. Skipping update.")
        return 0

    if not prospects_data:
        logger.warning("No prospect data returned from MLB Pipeline")
        return 0

    logger.info(f"Processing {len(prospects_data)} prospects")
    count = 0

    for item in prospects_data[:100]:
        name = item.get("name") or ""
        if not name:
            continue

        rank = item.get("rank")
        try:
            rank = int(rank) if rank else None
        except (ValueError, TypeError):
            rank = None

        mlb_id = str(item.get("mlb_id") or "")

        result = await db.execute(select(Prospect).where(Prospect.name == name))
        prospect = result.scalar_one_or_none()

        if prospect:
            old_rank = prospect.rank_current
            prospect.rank_previous = old_rank
            prospect.rank_current = rank
            if old_rank and rank:
                prospect.rank_change = old_rank - rank
                prospect.is_rising = prospect.rank_change >= RISING_THRESHOLD
            else:
                prospect.rank_change = 0
                prospect.is_rising = False
            prospect.position = item.get("position") or prospect.position
            prospect.team = item.get("team") or prospect.team
            prospect.eta = item.get("eta") or prospect.eta
            prospect.scouting_grade = item.get("grade") or prospect.scouting_grade
        else:
            prospect = Prospect(
                mlb_id=mlb_id or None,
                name=name,
                position=item.get("position"),
                team=item.get("team"),
                rank_current=rank,
                rank_previous=None,
                rank_change=0,
                eta=item.get("eta"),
                scouting_grade=item.get("grade"),
                is_rising=False,
                source="mlb_pipeline",
            )
            db.add(prospect)

        prospect.last_updated = datetime.now()
        count += 1

    await db.commit()
    return count


async def _fetch_mlb_pipeline() -> list[dict]:
    """Fetch and parse MLB Pipeline prospect rankings."""
    async with AsyncSession(impersonate="chrome124") as client:
        resp = await client.get(PROSPECTS_URL, timeout=30)
        logger.info(f"MLB Pipeline status: {resp.status_code} | size: {len(resp.text)} chars")

        if resp.status_code != 200:
            logger.error(f"MLB Pipeline non-200: {resp.status_code}")
            return []

        html = resp.text

        # Search full HTML for API endpoint URLs containing prospect-related paths
        api_patterns = re.findall(
            r'["\'](https?://[^\s"\'<>]*(?:prospect|pipeline|ranking|top.?100|milb)[^\s"\'<>]*)["\']',
            html, re.IGNORECASE
        )
        if api_patterns:
            logger.info(f"Found potential API URLs: {api_patterns[:10]}")

        # Also search for statsapi references
        statsapi_patterns = re.findall(r'["\'](https?://statsapi[^\s"\'<>]+)["\']', html)
        if statsapi_patterns:
            logger.info(f"Found statsapi URLs: {statsapi_patterns[:10]}")

        # Search for fetch/ajax calls with relative paths
        relative_patterns = re.findall(
            r'(?:fetch|axios|xhr|url)\s*[:(]\s*["\']([/][^\s"\'<>]*(?:prospect|pipeline|ranking)[^\s"\'<>]*)["\']',
            html, re.IGNORECASE
        )
        if relative_patterns:
            logger.info(f"Found relative API paths: {relative_patterns[:10]}")

        # Try known statsapi endpoint for minor league players with prospect hydration
        try:
            prospect_resp = await client.get(
                "https://statsapi.mlb.com/api/v1/people?sportIds=11,12,13&season=2025"
                "&hydrate=currentTeam,team,educationLevel&fields=people,id,fullName,"
                "primaryPosition,currentTeam,mlbDebutDate",
                timeout=20
            )
            logger.info(f"statsapi people status: {prospect_resp.status_code} | size: {len(prospect_resp.text)}")
            if prospect_resp.status_code == 200:
                logger.info(f"statsapi people snippet: {prospect_resp.text[:500]}")
        except Exception as e:
            logger.warning(f"statsapi test failed: {e}")

        # Try a candidate MLB content API
        for candidate in [
            "https://www.mlb.com/milb/prospects/top-100-prospects",
            "https://www.mlb.com/data/prospects.json",
            "https://www.mlb.com/milb/data/prospects/pipeline.json",
        ]:
            try:
                r = await client.get(candidate, timeout=10)
                logger.info(f"Candidate {candidate}: {r.status_code} | {len(r.text)} chars | snippet: {r.text[:200]}")
            except Exception as e:
                logger.warning(f"Candidate {candidate} failed: {e}")

        logger.warning("Could not extract prospect data yet — see logs above for API discovery")
        return []


def _parse_next_data(data: dict) -> list[dict]:
    """Recursively search __NEXT_DATA__ for prospect arrays."""
    results = []

    def search(obj):
        if isinstance(obj, list):
            # Check if this looks like a prospect list
            if obj and isinstance(obj[0], dict):
                fields = set(obj[0].keys())
                prospect_fields = {"name", "rank", "position", "team", "playerId", "player", "prospect"}
                if fields & prospect_fields:
                    for item in obj:
                        p = _normalize_prospect(item)
                        if p:
                            results.append(p)
                    return
            for item in obj:
                search(item)
        elif isinstance(obj, dict):
            for v in obj.values():
                search(v)

    search(data)
    return results


def _extract_prospects_from_dict(data: dict) -> list[dict]:
    """Try to find prospect arrays in arbitrary dict."""
    results = []

    def search(obj, depth=0):
        if depth > 8:
            return
        if isinstance(obj, list) and len(obj) >= 10:
            if obj and isinstance(obj[0], dict):
                p = _normalize_prospect(obj[0])
                if p and p.get("name"):
                    for item in obj:
                        normalized = _normalize_prospect(item)
                        if normalized:
                            results.append(normalized)
                    return
            for item in obj:
                search(item, depth + 1)
        elif isinstance(obj, dict):
            for v in obj.values():
                search(v, depth + 1)

    search(data)
    return results


def _normalize_prospect(item: dict) -> Optional[dict]:
    """Normalize varied prospect data shapes into a standard dict."""
    if not isinstance(item, dict):
        return None

    # Try common field name patterns
    name = (
        item.get("name") or
        item.get("playerName") or
        item.get("fullName") or
        item.get("PlayerName") or
        (item.get("player") or {}).get("fullName") if isinstance(item.get("player"), dict) else None
    )
    if not name:
        return None

    rank = item.get("rank") or item.get("Rank") or item.get("ranking") or item.get("prospectRank")
    position = (
        item.get("position") or
        item.get("pos") or
        item.get("Pos") or
        (item.get("primaryPosition") or {}).get("abbreviation") if isinstance(item.get("primaryPosition"), dict) else None
    )
    team = (
        item.get("team") or
        item.get("org") or
        item.get("organization") or
        item.get("Team") or
        (item.get("currentTeam") or {}).get("name") if isinstance(item.get("currentTeam"), dict) else None
    )
    grade = item.get("grade") or item.get("FV") or item.get("fv") or item.get("scoutingGrade")
    eta = item.get("eta") or item.get("ETA") or item.get("mlbEta")
    mlb_id = item.get("playerId") or item.get("mlbamid") or item.get("id") or item.get("PlayerID")

    return {
        "name": name,
        "rank": rank,
        "position": str(position) if position else None,
        "team": str(team) if team else None,
        "grade": f"{grade} FV" if grade and "FV" not in str(grade) else str(grade) if grade else None,
        "eta": str(eta) if eta else None,
        "mlb_id": str(mlb_id) if mlb_id else None,
    }


async def get_prospects(db: DBSession, rising_only: bool = False) -> list[Prospect]:
    query = select(Prospect).order_by(Prospect.rank_current.asc().nullslast())
    if rising_only:
        query = query.where(Prospect.is_rising == True)
    result = await db.execute(query)
    return result.scalars().all()
