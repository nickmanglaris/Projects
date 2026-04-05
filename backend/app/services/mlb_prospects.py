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

        # Attempt 1: parse the actual mlb.com/milb/prospects page for embedded data
        #            and collect app bundle URLs for token hunting
        page_bundles = await _fetch_page_and_extract_bundles(client)

        # Attempt 2: search bundles for Contentful token (site-core first, then page bundles)
        token = await _find_contentful_token(client, extra_urls=page_bundles)
        if token:
            logger.info(f"Found Contentful token: {token[:12]}...")
            prospects = await _fetch_from_contentful(client, token)
            if prospects:
                return prospects

        # Attempt 3: Contentful without auth (some spaces are publicly accessible)
        try:
            r = await client.get(
                f"{CONTENTFUL_BASE}/entries?content_type=prospect&limit=200&order=fields.rank",
                timeout=15,
            )
            logger.info(f"Contentful no-auth: {r.status_code} | {r.text[:300]}")
            if r.status_code == 200:
                data = r.json()
                items = data.get("items", [])
                if items:
                    logger.info(f"Contentful no-auth returned {len(items)} items")
                    return [n for i in items if (n := _normalize_contentful_item(i))]
        except Exception as e:
            logger.warning(f"Contentful no-auth failed: {e}")

        # Attempt 4: statsapi pipeline/top100 — some versions exposed ranking data
        statsapi_urls = [
            "https://statsapi.mlb.com/api/v1/pipeline/prospects?limit=100&season=2025",
            "https://statsapi.mlb.com/api/v1/prospects?season=2025&limit=100",
            "https://statsapi.mlb.com/api/v1/sports/11/players?season=2025&fields=players,id,fullName,primaryPosition,currentTeam,prospectRank,stats&gameType=R&limit=200",
        ]
        for url in statsapi_urls:
            try:
                r = await client.get(url, timeout=15)
                logger.info(f"statsapi {url.split('/')[-1].split('?')[0]}: {r.status_code} | {r.text[:300]}")
                if r.status_code == 200:
                    data = r.json()
                    # Try multiple possible response keys
                    for key in ("prospects", "players", "people", "items"):
                        raw = data.get(key, [])
                        if raw:
                            logger.info(f"  -> found {len(raw)} entries under '{key}'")
                            logger.info(f"  -> sample keys: {list(raw[0].keys()) if raw else []}")
                            logger.info(f"  -> sample: {raw[0]}")
                            parsed = _parse_draft_prospects(raw)
                            if parsed:
                                return parsed
            except Exception as e:
                logger.warning(f"statsapi url failed: {e}")

        # Attempt 5: draft/prospects fallback — at least returns graded amateur players
        try:
            r = await client.get(
                "https://statsapi.mlb.com/api/v1/draft/prospects/2025",
                timeout=20,
            )
            if r.status_code == 200:
                data = r.json()
                raw = data.get("prospects", [])
                logger.info(f"draft/prospects returned {len(raw)} entries")
                if raw:
                    logger.info(f"Sample fields: {list(raw[0].keys())}")
                    logger.info(f"Sample item: {raw[0]}")
                    parsed = _parse_draft_prospects(raw)
                    if parsed:
                        logger.info(f"Parsed {len(parsed)} prospects from draft/prospects fallback")
                        return parsed
        except Exception as e:
            logger.warning(f"draft/prospects failed: {e}")

        logger.warning("Could not retrieve prospect data from any source")
        return []


async def _fetch_page_and_extract_bundles(client: AsyncSession) -> list[str]:
    """Fetch the MLB Pipeline page, look for embedded JSON data, return JS bundle URLs."""
    bundle_urls = []
    try:
        resp = await client.get(PROSPECTS_URL, timeout=30)
        logger.info(f"Prospects page: {resp.status_code} | {len(resp.text)} chars")
        if resp.status_code != 200:
            return bundle_urls

        html = resp.text
        tree = HTMLParser(html)

        # Look for embedded JSON / __NEXT_DATA__
        for tag in tree.css("script"):
            src = tag.attributes.get("src") or ""
            # Collect JS bundles hosted on mlbstatic.com
            if "mlbstatic.com" in src and src.endswith(".js"):
                bundle_urls.append(src)
            # Look for inline JSON that might contain prospect data
            text = tag.text(strip=True)
            if text and ("prospect" in text.lower() or "pipeline" in text.lower()):
                logger.info(f"Inline script with prospects keyword: {text[:400]}")

        logger.info(f"Found {len(bundle_urls)} mlbstatic JS bundles in page HTML")
        if bundle_urls:
            logger.info(f"Bundle URLs: {bundle_urls[:5]}")

    except Exception as e:
        logger.warning(f"Page fetch failed: {e}")

    return bundle_urls


def _parse_draft_prospects(raw: list[dict]) -> list[dict]:
    """Parse statsapi draft/prospects response into normalized prospect dicts."""
    results = []
    for i, item in enumerate(raw):
        # Get player info (nested under 'person' or flat)
        person = item.get("person") or item
        name = person.get("fullName") or person.get("name") or ""
        if not name:
            continue

        # Position
        pos_info = item.get("primaryPosition") or person.get("primaryPosition") or {}
        position = pos_info.get("abbreviation") or pos_info.get("name") if isinstance(pos_info, dict) else str(pos_info)

        # Team / school / organization
        school = item.get("school") or {}
        team_info = item.get("currentTeam") or item.get("team") or {}
        team = (team_info.get("name") if isinstance(team_info, dict) else str(team_info)) or \
               (school.get("name") if isinstance(school, dict) else None)

        # Prospect ranking / grade
        rank = item.get("rank") or item.get("prospectRank") or (i + 1)
        grade = item.get("scoutingReport") or item.get("grade") or item.get("overallGrade")

        # ETA / school year
        eta = item.get("draftEligibleYear") or item.get("eta")

        mlb_id = str(person.get("id") or item.get("bisPlayerId") or "")

        results.append({
            "name": name,
            "rank": rank,
            "position": str(position) if position else None,
            "team": str(team) if team else None,
            "grade": str(grade) if grade else None,
            "eta": str(eta) if eta else None,
            "mlb_id": mlb_id,
        })

    return results




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


async def _find_contentful_token(client: AsyncSession, extra_urls: list[str] | None = None) -> Optional[str]:
    """Search JS bundles for the Contentful delivery API token."""
    urls_to_search = [SITE_CORE_URL] + (extra_urls or [])

    for url in urls_to_search[:10]:  # cap at 10 bundles
        try:
            logger.info(f"Searching for token in: {url[-80:]}")
            resp = await client.get(url, timeout=30)
            if resp.status_code != 200:
                continue
            js = resp.text
            logger.info(f"  bundle size: {len(js)} chars")

            for pattern in TOKEN_PATTERNS:
                matches = re.findall(pattern, js, re.IGNORECASE)
                if matches:
                    candidates = [m for m in matches if len(m) > 20]
                    if candidates:
                        logger.info(f"Token candidates in {url[-40:]} ({pattern[:40]}): {[c[:16]+'...' for c in candidates[:3]]}")
                        return candidates[0]

            # Log space ID context if found
            idx = js.find("iiozhi00a8lc")
            if idx >= 0:
                logger.info(f"Space ID in {url[-40:]}: ...{js[max(0,idx-100):idx+200]}...")

        except Exception as e:
            logger.warning(f"Token search failed for {url[-60:]}: {e}")

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
