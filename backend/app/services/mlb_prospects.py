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


CONTENTFUL_SPACE = "iiozhi00a8lc"
CONTENTFUL_BASE = f"https://cdn.contentful.com/spaces/{CONTENTFUL_SPACE}"


async def _fetch_mlb_pipeline() -> list[dict]:
    """Fetch MLB Pipeline prospect rankings."""
    async with AsyncSession(impersonate="chrome124") as client:

        # Attempt 1: find Contentful token in site-core bundle
        token = await _find_contentful_token(client)
        if token:
            logger.info(f"Found Contentful token: {token[:12]}...")
            prospects = await _fetch_from_contentful(client, token)
            if prospects:
                return prospects

        # Attempt 2: MLB lookup service (older public MLB API)
        lookup_urls = [
            "https://lookup-service-prod.mlb.com/json/named.prospect_list.bam?sport_code=%27b%27&season=2025",
            "https://lookup-service-prod.mlb.com/json/named.search_player_all.bam?sport_code=%27b%27&active_sw=%27Y%27&name_part=%27a%25%27",
        ]
        for url in lookup_urls:
            try:
                r = await client.get(url, timeout=15)
                logger.info(f"lookup-service {url[-50:]}: {r.status_code} | {r.text[:400]}")
            except Exception as e:
                logger.warning(f"lookup-service failed: {e}")

        # Attempt 3: search site-core for other bundle URLs
        await _find_app_bundles(client)

        # Attempt 4: direct MLB Pipeline API candidates
        api_candidates = [
            "https://www.mlb.com/milb/prospects/api/v1/prospects",
            "https://www.mlb.com/milb/prospects/api/prospects",
            "https://www.mlb.com/milb/prospects/api/top100",
            "https://content.mlb.com/milb/prospects",
            "https://statsapi.mlb.com/api/v1/draft/prospects/2025",
        ]
        for url in api_candidates:
            try:
                r = await client.get(url, timeout=10)
                logger.info(f"API candidate {url}: {r.status_code} | {r.text[:300]}")
            except Exception as e:
                logger.warning(f"Candidate failed {url}: {e}")

        logger.warning("Could not retrieve prospect data from any source")
        return []


async def _find_app_bundles(client: AsyncSession):
    """Search site-core.min.js for dynamically loaded bundle URLs."""
    try:
        resp = await client.get(SITE_CORE_URL, timeout=30)
        if resp.status_code != 200:
            return
        js = resp.text
        # Look for chunk/bundle URLs
        bundle_urls = re.findall(r'https?://[^\s"\'<>]+\.js[^\s"\'<>]*', js)
        logger.info(f"Bundle URLs in site-core: {bundle_urls[:10]}")
        # Look for any API base URL
        api_bases = re.findall(r'https?://[^\s"\'<>]*(?:api|content|data|pipeline)[^\s"\'<>]{0,50}', js)
        logger.info(f"API base URLs in site-core: {api_bases[:10]}")
    except Exception as e:
        logger.warning(f"Bundle search failed: {e}")


SITE_CORE_URL = "https://builds.mlbstatic.com/mlb.com/builds/site-core/1758062334267/site-core.min.js"

TOKEN_PATTERNS = [
    r'accessToken["\s:]+["\']([A-Za-z0-9_\-]{20,60})["\']',
    r'deliveryToken["\s:]+["\']([A-Za-z0-9_\-]{20,60})["\']',
    r'contentful[^"\']{0,30}["\']([A-Za-z0-9_\-]{40,60})["\']',
    r'CONTENTFUL_ACCESS_TOKEN["\s:=]+["\']([A-Za-z0-9_\-]{20,60})["\']',
    r'iiozhi00a8lc[^"\']{0,30}["\']([A-Za-z0-9_\-]{40,60})["\']',
    r'"token"\s*:\s*"([A-Za-z0-9_\-]{40,60})"',
    r'space["\s:]+["\']iiozhi00a8lc["\'][^}]{0,200}["\']([A-Za-z0-9_\-]{40,60})["\']',
]


async def _find_contentful_token(client: AsyncSession) -> Optional[str]:
    """Search the site-core JS bundle for the Contentful delivery API token."""
    try:
        logger.info(f"Fetching site-core bundle: {SITE_CORE_URL}")
        resp = await client.get(SITE_CORE_URL, timeout=30)
        logger.info(f"site-core bundle: {resp.status_code} | {len(resp.text)} chars")
        if resp.status_code != 200:
            return None

        js = resp.text

        for pattern in TOKEN_PATTERNS:
            matches = re.findall(pattern, js, re.IGNORECASE)
            if matches:
                # Filter out obvious non-tokens (too short, common words)
                candidates = [m for m in matches if len(m) > 20]
                if candidates:
                    logger.info(f"Token candidates ({pattern[:40]}): {[c[:16]+'...' for c in candidates[:3]]}")
                    return candidates[0]

        # Log any occurrence of the space ID with surrounding context
        idx = js.find("iiozhi00a8lc")
        if idx >= 0:
            logger.info(f"Space ID context: ...{js[max(0,idx-100):idx+200]}...")

    except Exception as e:
        logger.warning(f"Token search in site-core failed: {e}")
    return None


async def _fetch_from_contentful(client: AsyncSession, token: str) -> list[dict]:
    """Query Contentful for prospect entries."""
    headers = {"Authorization": f"Bearer {token}"}

    # First get available content types
    try:
        ct_resp = await client.get(
            f"{CONTENTFUL_BASE}/content_types?limit=50",
            headers=headers, timeout=15
        )
        logger.info(f"Contentful content_types: {ct_resp.status_code} | {ct_resp.text[:500]}")
    except Exception as e:
        logger.warning(f"Contentful content_types failed: {e}")

    # Try common content type names for prospects
    for ct in ["prospect", "prospectsPlayer", "mlbPlayer", "player", "pipelinePlayer"]:
        try:
            r = await client.get(
                f"{CONTENTFUL_BASE}/entries?content_type={ct}&limit=200&order=fields.rank",
                headers=headers, timeout=15
            )
            logger.info(f"Contentful content_type={ct}: {r.status_code} | {r.text[:300]}")
            if r.status_code == 200:
                data = r.json()
                items = data.get("items", [])
                if items:
                    logger.info(f"Found {len(items)} items with content_type={ct}")
                    return [_normalize_contentful_item(i) for i in items if _normalize_contentful_item(i)]
        except Exception as e:
            logger.warning(f"Contentful ct={ct} failed: {e}")

    return []


def _normalize_contentful_item(item: dict) -> Optional[dict]:
    fields = item.get("fields", {})
    if not fields:
        return None
    name = fields.get("name") or fields.get("playerName") or fields.get("fullName")
    if not name:
        return None
    return {
        "name": name,
        "rank": fields.get("rank") or fields.get("ranking"),
        "position": fields.get("position") or fields.get("pos"),
        "team": fields.get("team") or fields.get("organization") or fields.get("org"),
        "grade": fields.get("grade") or fields.get("fv") or fields.get("scoutingGrade"),
        "eta": fields.get("eta") or fields.get("mlbEta"),
        "mlb_id": fields.get("mlbId") or fields.get("playerId"),
    }


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
