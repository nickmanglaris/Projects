from datetime import datetime
from fastapi import APIRouter, HTTPException
from app.schemas.research import ResearchRequest, ResearchResponse, ResearchResult
from app.services.ebay_scraper import scrape_raw_listings

router = APIRouter(prefix="/research", tags=["research"])


@router.post("/search", response_model=ResearchResponse)
async def search_cards(req: ResearchRequest):
    try:
        listings = await scrape_raw_listings(
            player_name=req.player_name,
            year=req.year,
            variation=req.variation,
            min_price=req.min_price,
            max_price=req.max_price,
            max_results=req.max_results,
        )
    except RuntimeError as e:
        if "rate_limited" in str(e):
            raise HTTPException(
                status_code=503,
                detail="eBay is temporarily rate limiting requests. Please try again in 15 minutes.",
            )
        raise HTTPException(status_code=500, detail=str(e))

    if not listings:
        raise HTTPException(
            status_code=404,
            detail=f"No raw card listings found. Try different search terms or check the backend console for scrape logs.",
        )

    parts = []
    if req.year:
        parts.append(str(req.year))
    parts.append(req.player_name)
    if req.variation:
        parts.append(req.variation)
    query = " ".join(parts)

    prices = [r["price"] for r in listings if r.get("price")]
    avg_price = round(sum(prices) / len(prices), 2) if prices else None
    price_range = {"min": min(prices), "max": max(prices)} if prices else None

    return ResearchResponse(
        results=[ResearchResult(**{k: v for k, v in r.items() if k != "analysis"}) for r in listings],
        query=query,
        scraped_at=datetime.now(),
        total_found=len(listings),
        avg_price=avg_price,
        price_range=price_range,
        ai_analysis_enabled=False,
    )
