from datetime import date, datetime
from typing import Optional
from pydantic import BaseModel


class ProspectOut(BaseModel):
    id: int
    name: str
    position: Optional[str] = None
    team: Optional[str] = None
    rank_current: Optional[int] = None
    rank_previous: Optional[int] = None
    rank_change: int = 0
    eta: Optional[str] = None
    scouting_grade: Optional[str] = None
    is_rising: bool = False
    last_updated: Optional[datetime] = None
    source: str

    model_config = {"from_attributes": True}


class ProspectsResponse(BaseModel):
    prospects: list[ProspectOut]
    last_updated: Optional[datetime] = None
    total: int


class CardOut(BaseModel):
    id: int
    card_name: str
    player_name: Optional[str] = None
    year: Optional[int] = None
    variation: Optional[str] = None
    grade: Optional[str] = None
    is_owned: bool
    is_watchlist: bool
    purchase_price: Optional[float] = None

    model_config = {"from_attributes": True}


class PriceHistoryOut(BaseModel):
    id: int
    card_id: int
    snapshot_date: str
    avg_sale_price: Optional[float] = None
    min_price: Optional[float] = None
    max_price: Optional[float] = None
    sample_count: int
    psa10_price: Optional[float] = None
    psa9_price: Optional[float] = None
    psa8_price: Optional[float] = None

    model_config = {"from_attributes": True}


class WatchlistEntry(BaseModel):
    card: CardOut
    latest_price: Optional[float] = None
    price_change_pct: Optional[float] = None
    suggested_list_price: Optional[float] = None
    latest_psa10: Optional[float] = None
    latest_psa9: Optional[float] = None
    latest_psa8: Optional[float] = None
    price_history: list[PriceHistoryOut] = []


class GradingSubmissionCreate(BaseModel):
    player_name: str
    year: Optional[int] = None
    card_set: str
    variation: Optional[str] = None
    card_number: Optional[str] = None
    psa_order_number: Optional[str] = None
    submitted_date: Optional[date] = None
    estimated_return: Optional[date] = None
    status: str = "submitted"
    purchase_price: Optional[float] = None
    grading_fee: Optional[float] = None
    notes: Optional[str] = None


class GradingSubmissionUpdate(BaseModel):
    status: Optional[str] = None
    grade_received: Optional[int] = None
    cert_number: Optional[str] = None
    estimated_return: Optional[date] = None
    psa_order_number: Optional[str] = None
    notes: Optional[str] = None


class GradingSubmissionOut(BaseModel):
    id: int
    player_name: str
    year: Optional[int] = None
    card_set: str
    variation: Optional[str] = None
    card_number: Optional[str] = None
    psa_order_number: Optional[str] = None
    submitted_date: Optional[date] = None
    estimated_return: Optional[date] = None
    status: str
    grade_received: Optional[int] = None
    cert_number: Optional[str] = None
    purchase_price: Optional[float] = None
    grading_fee: Optional[float] = None
    notes: Optional[str] = None
    created_at: datetime

    model_config = {"from_attributes": True}
