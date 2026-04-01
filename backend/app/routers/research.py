from datetime import datetime
from fastapi import APIRouter, HTTPException
from app.schemas.research import ResearchRequest, ResearchResponse, ResearchResult
from app.services.ebay_scraper import scrape_completed_listings

router = APIRouter(prefix="/research", tags=["research"])


@router.post("/search", response_model=ResearchResponse)
async def search_cards(req: ResearchRequest):
    try:
        results = await scrape_completed_listings(
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

    prices = [r["price"] for r in results if r.get("price")]
    avg_price = round(sum(prices) / len(prices), 2) if prices else None
    price_range = {"min": min(prices), "max": max(prices)} if prices else None

    parts = []
    if req.year:
        parts.append(str(req.year))
    parts.append(req.player_name)
    if req.variation:
        parts.append(req.variation)
    parts.append("PSA 10")
    query = " ".join(parts)

    return ResearchResponse(
        results=[ResearchResult(**r) for r in results],
        query=query,
        scraped_at=datetime.now(),
        total_found=len(results),
        avg_price=avg_price,
        price_range=price_range,
    )
