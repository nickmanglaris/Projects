from fastapi import APIRouter, HTTPException

from app.config import settings
from app.services.ebay_inventory import fetch_active_listings

router = APIRouter(prefix="/inventory", tags=["inventory"])


@router.get("/listings")
async def get_active_listings(flag_after_days: int = 30):
    """
    Return all active eBay listings with days-listed and stale flag.
    flag_after_days: listings older than this are marked stale (default 30).
    """
    if not settings.ebay_token_set:
        raise HTTPException(status_code=400, detail="EBAY_USER_TOKEN not set in .env")

    listings = await fetch_active_listings(settings.EBAY_USER_TOKEN)

    total_value = sum(l["price"] * l["quantity"] for l in listings)
    stale = [l for l in listings if l["days_listed"] >= flag_after_days]

    return {
        "listings": listings,
        "total_listings": len(listings),
        "total_value": round(total_value, 2),
        "stale_count": len(stale),
        "flag_after_days": flag_after_days,
    }
