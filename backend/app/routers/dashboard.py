from typing import Optional
from fastapi import APIRouter, Depends, Query
from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.database import get_db
from app.models.transaction import Transaction
from app.schemas.dashboard import DashboardSummary, TrajectoryResponse, TrajectoryPoint
from app.schemas.transaction import TransactionCreate, TransactionListResponse, TransactionOut, TransactionUpdate
from app.services import ebay_mock
from datetime import date, timedelta

router = APIRouter(prefix="/dashboard", tags=["dashboard"])


def _period_to_days(period: str) -> int:
    return {"30d": 30, "90d": 90, "6m": 180, "12m": 365, "all": 3650}.get(period, 365)


@router.get("/summary", response_model=DashboardSummary)
async def get_summary(period: str = Query("12m"), db: AsyncSession = Depends(get_db)):
    if not settings.ebay_connected:
        return DashboardSummary(**ebay_mock.get_mock_summary(period))

    days = _period_to_days(period)
    cutoff = date.today() - timedelta(days=days)

    sales = await db.execute(
        select(Transaction).where(
            and_(Transaction.transaction_type == "sale", Transaction.transaction_date >= cutoff)
        )
    )
    purchases = await db.execute(
        select(Transaction).where(
            and_(Transaction.transaction_type == "purchase", Transaction.transaction_date >= cutoff)
        )
    )
    sales_list = sales.scalars().all()
    purchases_list = purchases.scalars().all()

    revenue = sum(t.amount for t in sales_list)
    cost = sum(t.amount + t.shipping_cost for t in purchases_list)
    profit = sum((t.net_amount or 0) for t in sales_list) - cost + sum(t.amount for t in purchases_list)
    revenue_total = round(revenue, 2)
    cost_total = round(cost, 2)
    profit_total = round(revenue_total - sum(t.ebay_fees + t.shipping_cost for t in sales_list) - cost_total, 2)
    roi_pct = round((profit_total / cost_total * 100) if cost_total > 0 else 0, 1)

    return DashboardSummary(
        revenue_total=revenue_total,
        cost_total=cost_total,
        profit_total=profit_total,
        roi_pct=roi_pct,
        period=period,
        is_mock=False,
        transaction_count=len(sales_list) + len(purchases_list),
        avg_profit_per_card=round(profit_total / max(len(sales_list), 1), 2),
    )


@router.get("/trajectory", response_model=TrajectoryResponse)
async def get_trajectory(period: str = Query("12m"), db: AsyncSession = Depends(get_db)):
    if not settings.ebay_connected:
        data = [TrajectoryPoint(**p) for p in ebay_mock.get_mock_trajectory(period)]
        return TrajectoryResponse(data=data, period=period, is_mock=True)

    days = _period_to_days(period)
    cutoff = date.today() - timedelta(days=days)

    result = await db.execute(
        select(Transaction).where(Transaction.transaction_date >= cutoff).order_by(Transaction.transaction_date)
    )
    txns = result.scalars().all()

    from collections import defaultdict
    monthly: dict[str, dict] = defaultdict(lambda: {"revenue": 0.0, "cost": 0.0, "fees": 0.0, "ship_sell": 0.0})
    for t in txns:
        month = t.transaction_date.strftime("%Y-%m")
        if t.transaction_type == "sale":
            monthly[month]["revenue"] += t.amount
            monthly[month]["fees"] += t.ebay_fees
            monthly[month]["ship_sell"] += t.shipping_cost
        else:
            monthly[month]["cost"] += t.amount + t.shipping_cost

    data = []
    cumulative = 0.0
    for month in sorted(monthly.keys()):
        d = monthly[month]
        profit = d["revenue"] - d["fees"] - d["ship_sell"] - d["cost"]
        cumulative += profit
        data.append(TrajectoryPoint(
            date=month,
            revenue=round(d["revenue"], 2),
            cost=round(d["cost"], 2),
            profit=round(profit, 2),
            cumulative_profit=round(cumulative, 2),
        ))

    return TrajectoryResponse(data=data, period=period, is_mock=False)


@router.get("/transactions", response_model=TransactionListResponse)
async def list_transactions(
    page: int = Query(1, ge=1),
    limit: int = Query(50, ge=1, le=200),
    tx_type: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db),
):
    query = select(Transaction).order_by(Transaction.transaction_date.desc())
    count_query = select(func.count()).select_from(Transaction)

    if tx_type:
        query = query.where(Transaction.transaction_type == tx_type)
        count_query = count_query.where(Transaction.transaction_type == tx_type)

    total_result = await db.execute(count_query)
    total = total_result.scalar() or 0

    offset = (page - 1) * limit
    query = query.offset(offset).limit(limit)
    result = await db.execute(query)
    items = result.scalars().all()

    return TransactionListResponse(
        items=[TransactionOut.model_validate(t) for t in items],
        total=total,
        page=page,
        limit=limit,
    )


@router.post("/transactions", response_model=TransactionOut, status_code=201)
async def create_transaction(data: TransactionCreate, db: AsyncSession = Depends(get_db)):
    net = data.amount - data.ebay_fees - data.shipping_cost
    if data.transaction_type == "purchase":
        net = -(data.amount + data.shipping_cost)
    tx = Transaction(**data.model_dump(), net_amount=net)
    db.add(tx)
    await db.commit()
    await db.refresh(tx)
    return TransactionOut.model_validate(tx)


@router.patch("/transactions/{tx_id}", response_model=TransactionOut)
async def update_transaction(tx_id: int, data: TransactionUpdate, db: AsyncSession = Depends(get_db)):
    from fastapi import HTTPException
    result = await db.execute(select(Transaction).where(Transaction.id == tx_id))
    tx = result.scalar_one_or_none()
    if not tx:
        raise HTTPException(status_code=404, detail="Transaction not found")
    for field, val in data.model_dump(exclude_none=True).items():
        setattr(tx, field, val)
    await db.commit()
    await db.refresh(tx)
    return TransactionOut.model_validate(tx)
