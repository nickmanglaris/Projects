from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.database import get_db
from app.models.transaction import Transaction
from app.services import ebay_mock
from app.services.ebay_oauth import generate_auth_url, handle_callback, get_auth_status, disconnect
from app.services.ebay_trading import fetch_ebay_sales

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
        return {"connected": False, "mock_mode": True, "token_set": False}
    return {
        **(await get_auth_status(db)),
        "token_set": settings.ebay_token_set,
    }


@router.post("/auth/disconnect")
async def auth_disconnect(db: AsyncSession = Depends(get_db)):
    await disconnect(db)
    return {"disconnected": True}


@router.post("/sync/sales")
async def sync_sales(days: int = 90, db: AsyncSession = Depends(get_db)):
    """
    Pull sales from eBay Sell Finances API and save new ones to the database.
    Uses EBAY_USER_TOKEN from .env. Skips duplicates by ebay_item_id.
    """
    if not settings.ebay_token_set:
        raise HTTPException(status_code=400, detail="EBAY_USER_TOKEN not set in .env")

    raw = await fetch_ebay_sales(settings.EBAY_USER_TOKEN, days=days)

    created = 0
    skipped = 0
    for item in raw:
        order_id = item.get("ebay_item_id", "")

        # Skip duplicates
        if order_id:
            existing = await db.execute(
                select(Transaction).where(Transaction.ebay_item_id == order_id)
            )
            if existing.scalar_one_or_none():
                skipped += 1
                continue

        net = round(item["amount"] - item["ebay_fees"] - item["shipping_cost"], 2)
        tx = Transaction(
            ebay_item_id=order_id or None,
            transaction_type="sale",
            card_name=item["card_name"],
            amount=item["amount"],
            ebay_fees=item["ebay_fees"],
            shipping_cost=item["shipping_cost"],
            net_amount=net,
            transaction_date=item["transaction_date"],
            source="ebay",
            reconciled=True,
        )
        db.add(tx)
        created += 1

    await db.commit()
    return {"synced": created, "skipped_duplicates": skipped, "total_from_ebay": len(raw)}


@router.get("/purchases")
async def get_purchases(days: int = 90, db: AsyncSession = Depends(get_db)):
    if not settings.ebay_connected:
        return {"mock": True, "items": ebay_mock.get_mock_transactions(days, "purchase")}
    result = await db.execute(
        select(Transaction).where(Transaction.transaction_type == "purchase").limit(100)
    )
    items = result.scalars().all()
    return {"mock": False, "items": [{"card_name": t.card_name, "amount": t.amount, "date": str(t.transaction_date)} for t in items]}


@router.get("/sales")
async def get_sales(days: int = 90, db: AsyncSession = Depends(get_db)):
    if not settings.ebay_connected:
        return {"mock": True, "items": ebay_mock.get_mock_transactions(days, "sale")}
    result = await db.execute(
        select(Transaction).where(Transaction.transaction_type == "sale").limit(100)
    )
    items = result.scalars().all()
    return {"mock": False, "items": [{"card_name": t.card_name, "amount": t.amount, "date": str(t.transaction_date)} for t in items]}
