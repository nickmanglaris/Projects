from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.database import get_db
from app.services import ebay_mock
from app.services.ebay_oauth import generate_auth_url, handle_callback, get_auth_status, disconnect

router = APIRouter(prefix="/ebay", tags=["ebay"])


@router.get("/auth/url")
async def get_auth_url(db: AsyncSession = Depends(get_db)):
    if not settings.EBAY_CLIENT_ID or settings.EBAY_CLIENT_ID == "YOUR_CLIENT_ID_HERE":
        raise HTTPException(status_code=400, detail="eBay client ID not configured. Set EBAY_CLIENT_ID in .env")
    url = await generate_auth_url(db)
    return {"auth_url": url}


@router.get("/auth/callback")
async def oauth_callback(code: str, state: str, db: AsyncSession = Depends(get_db)):
    try:
        result = await handle_callback(db, code, state)
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/auth/status")
async def auth_status(db: AsyncSession = Depends(get_db)):
    if not settings.ebay_connected:
        return {"connected": False, "mock_mode": True, "expires_at": None}
    return await get_auth_status(db)


@router.post("/auth/disconnect")
async def auth_disconnect(db: AsyncSession = Depends(get_db)):
    await disconnect(db)
    return {"disconnected": True}


@router.get("/purchases")
async def get_purchases(days: int = 90, db: AsyncSession = Depends(get_db)):
    if not settings.ebay_connected:
        return {"mock": True, "items": ebay_mock.get_mock_transactions(days, "purchase")}
    # Real eBay API call would go here
    raise HTTPException(status_code=501, detail="Real eBay API not yet integrated")


@router.get("/sales")
async def get_sales(days: int = 90, db: AsyncSession = Depends(get_db)):
    if not settings.ebay_connected:
        return {"mock": True, "items": ebay_mock.get_mock_transactions(days, "sale")}
    raise HTTPException(status_code=501, detail="Real eBay API not yet integrated")
