from datetime import date, datetime
from typing import Optional
from pydantic import BaseModel, computed_field


class TransactionBase(BaseModel):
    card_name: str
    player_name: Optional[str] = None
    year: Optional[int] = None
    variation: Optional[str] = None
    grade: Optional[str] = None
    amount: float
    ebay_fees: float = 0.0
    shipping_cost: float = 0.0
    transaction_date: date
    transaction_type: str  # 'purchase' | 'sale'
    source: str = "manual"
    notes: Optional[str] = None


class TransactionCreate(TransactionBase):
    ebay_item_id: Optional[str] = None


class TransactionUpdate(BaseModel):
    card_name: Optional[str] = None
    amount: Optional[float] = None
    ebay_fees: Optional[float] = None
    shipping_cost: Optional[float] = None
    transaction_date: Optional[date] = None
    notes: Optional[str] = None
    reconciled: Optional[bool] = None


class TransactionOut(TransactionBase):
    id: int
    ebay_item_id: Optional[str] = None
    net_amount: Optional[float] = None
    reconciled: bool
    created_at: datetime

    model_config = {"from_attributes": True}


class TransactionListResponse(BaseModel):
    items: list[TransactionOut]
    total: int
    page: int
    limit: int
